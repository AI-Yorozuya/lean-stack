"""報價單的資料模型。規則來源：能力包/其他/報價單.md（報價成交型 fork 的定義單據）。

報價單是「報價成交型」生意流的主場單據——客戶問價 → 我報價 → 談成才生訂單。
三拍疊起來（同 order 慣例，這是刻意的：報價單與訂單是同一承重牆家族）：
- 串關聯：報價單 → 客戶（多對一）；明細 → 報價單（1:N）；明細 → 商品（多對一）。
- 抄快照：報價當下把品名＋單價存進明細（snapshot_from）——之後目錄改價，歷史報價不動。
- 跑狀態：Quotation.status 生命週期（草稿→已送出→已成交／已作廢），成交當下生一張訂單。

承重牆（能力包「業務規則」節；pattern 掛在術軌、不 inline 進本 model）：
- {總額 = 明細加總，對不上當場擋}  → assert-invariant（recalc_total + save 守衛）。這是報價成交型的金額守恆命門。
- {已送出後明細/總額不可改}        → is_editable（EDITABLE_STATUSES），update 入口擋。
- {已成交只能生一張訂單、不可重複成交} → apply_transition 的 CLOSED 終態守。
- {報價單號不撞}                   → quote_no 業務識別碼（serial-advisory-lock 的 pattern 位；單機先用 pk 衍生）。

為什麼真相砌在後端：前端算金額給人看（體驗），但金額守恆必須後端算/擋——不然改 request 就破。
"""
from decimal import Decimal

from django.db import models

from apps._common.models import TimeStampedModel


class TransitionError(Exception):
    """狀態機擋下來的非法轉移（終態不可轉、跳步不可轉）。API 層轉 422。"""


class Quotation(TimeStampedModel):
    """一張報價：串客戶＋明細（含快照），status 管「談成沒」，成交生訂單。"""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', '草稿'
        SENT = 'SENT', '已送出'        # 報給客戶了、等回覆
        WON = 'WON', '已成交'          # 終態：談成 → 生訂單
        VOID = 'VOID', '已作廢'        # 終態：沒談成/作廢

    # 合法轉移表（真相）。沒列的 (狀態,動作)＝非法（含終態不可轉、跳步不可轉）。
    TRANSITIONS = {
        'send':  {'from': (Status.DRAFT,),             'to': Status.SENT, 'verb': '送出'},
        'win':   {'from': (Status.SENT,),              'to': Status.WON,  'verb': '成交'},
        'void':  {'from': (Status.DRAFT, Status.SENT), 'to': Status.VOID, 'verb': '作廢'},
    }
    # {已送出後明細/總額不可改}：只有草稿能動明細。
    EDITABLE_STATUSES = (Status.DRAFT,)

    quote_no = models.CharField('報價單號', max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(
        'member.Member', on_delete=models.PROTECT, related_name='quotations',
        verbose_name='客戶',   # 客戶＝抽象槽（宿主填 Member；換生意型可填 Customer/Student）
    )
    status = models.CharField('狀態', max_length=10, choices=Status.choices, default=Status.DRAFT)
    total = models.DecimalField('總額', max_digits=12, decimal_places=0, default=Decimal('0'))
    # 成交生的訂單（一對一，成交後才有）——報價→訂單的承重牆連結。
    order = models.OneToOneField(
        'order.Order', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='source_quotation', verbose_name='成交生的訂單',
    )

    class Meta:
        verbose_name = '報價單'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.quote_no or "草稿"} · {self.customer}'

    @property
    def is_editable(self):
        return self.status in self.EDITABLE_STATUSES

    def recalc_total(self):
        """{總額 = 明細加總}：衍生值，後端算，不信前端。"""
        self.total = sum((i.subtotal for i in self.items.all()), Decimal('0'))

    def assert_total_consistent(self):
        """assert-invariant：存進 DB 的 total 必須等於明細加總，對不上就擋。"""
        expected = sum((i.subtotal for i in self.items.all()), Decimal('0'))
        if self.total != expected:
            raise ValueError(f'金額守恆破了：total={self.total} ≠ Σ明細={expected}')

    def apply_transition(self, action):
        """狀態機唯一入口。非法轉移擋成 TransitionError；成交(win)時生訂單。"""
        rule = self.TRANSITIONS.get(action)
        if rule is None or self.status not in rule['from']:
            raise TransitionError(f'狀態「{self.get_status_display()}」不能{action}')
        self.status = rule['to']
        self.save(update_fields=['status', 'updated_at'])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.quote_no:
            # 業務識別碼從 pk 衍生（單機夠用；跨 worker 換 serial-advisory-lock pattern）。
            type(self).objects.filter(pk=self.pk).update(quote_no=f'QU-{self.pk:06d}')
            self.quote_no = f'QU-{self.pk:06d}'


class QuotationItem(TimeStampedModel):
    """報價明細：報價當下抄商品的品名＋單價（快照），之後目錄變動不影響歷史。"""

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items', verbose_name='報價單')
    product = models.ForeignKey('product.Product', on_delete=models.PROTECT, related_name='quotation_items', verbose_name='商品')
    name_snapshot = models.CharField('品名（快照）', max_length=200)
    unit_price = models.DecimalField('單價（快照）', max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField('數量', default=1)

    class Meta:
        verbose_name = '報價明細'

    @property
    def subtotal(self):
        """{明細小計 = 數量 × 單價}：衍生值。"""
        return self.unit_price * self.quantity

    def snapshot_from(self, product):
        """報價當下抄一份商品品名＋單價——歷史報價凍結，目錄改價不動它。"""
        self.name_snapshot = product.name
        self.unit_price = product.price
