"""報價單的資料模型。規則來源：能力包/其他/報價單.md（報價成交型 fork 的定義單據）。

報價單是「報價成交型」生意流的主場單據——客戶問價 → 我報價 → 談成才生訂單。
三拍疊起來（**刻意跟 order 同一個形**：報價單與訂單是同一承重牆家族，看完 order 這裡零學習成本）：
- 串關聯：報價單 → 客戶（多對一）；明細 → 報價單（1:N）；明細 → 商品（多對一）。
- 抄快照：報價當下把品名＋單價存進明細（snapshot_from）——之後目錄改價，歷史報價不動。
- 跑狀態：Quotation.status 生命週期（草稿→已送出→已成交／已作廢），成交當下生一張訂單。

跟 order 唯一的加碼——**成交生訂單的承重牆**（apply_transition 的 win）：
報價談成 → 把報價當下凍結的明細搬進一張新訂單，用**報價的凍結價**成交（不重讀目錄現價）。
報價單:訂單 = 1:1，成交後 source_quotation 反指得回來。

承重牆（能力包「業務規則」節；pattern 掛在術軌、不 inline 進本 model）：
- {總額 = 明細加總，對不上當場擋}  → assert-invariant（recalc_total 算＋assert_total_consistent 守）。
- {已送出後明細/總額不可改}        → is_editable（EDITABLE_STATUSES），update 入口擋。
- {已成交只生一張訂單、不可重複成交} → apply_transition 的終態守 ＋ order OneToOne。
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
        'send': {'from': (Status.DRAFT,),             'to': Status.SENT, 'verb': '送出'},
        'win':  {'from': (Status.SENT,),              'to': Status.WON,  'verb': '成交'},
        'void': {'from': (Status.DRAFT, Status.SENT), 'to': Status.VOID, 'verb': '作廢'},
    }
    # {已送出後明細/總額不可改}：只有草稿能動明細。
    EDITABLE_STATUSES = (Status.DRAFT,)

    # 業務識別碼（單號）≠ DB 主鍵：對外看 quote_no，pk 是內部的事（同 order.order_no）。
    quote_no = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(
        'member.Member',
        on_delete=models.PROTECT,          # 有報價的客戶不准刪——歷史要留（呼應「停用不刪」）
        related_name='quotations',
    )  # 客戶＝抽象槽（宿主填 Member；換生意型可填 Customer/Student）
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    # 總額永遠是「算出來的」（recalc_total），欄位只是快取查詢方便（同 order）。
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    # 成交生的訂單（1:1，成交後才有）——報價→訂單的承重牆連結。SET_NULL：訂單沒了報價紀錄還在。
    order = models.OneToOneField(
        'order.Order',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='source_quotation',
    )
    note = models.CharField(max_length=200, blank=True)  # 備註（自由文字，選填）

    def __str__(self):
        return f'{self.quote_no or "草稿"} {self.customer} ${self.total} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        """建立後補上單號 quote_no（需先存拿到 pk，再從 pk 衍生；同 order.save）。"""
        super().save(*args, **kwargs)
        if not self.quote_no:
            self.quote_no = f'QU-{self.pk:06d}'
            Quotation.objects.filter(pk=self.pk).update(quote_no=self.quote_no)

    def recalc_total(self):
        """{總額 = 明細加總}：衍生值，後端算，不信前端。明細有增刪改後呼叫。"""
        self.total = sum((item.subtotal for item in self.items.all()), Decimal('0'))
        self.save(update_fields=['total', 'updated_at'])

    def assert_total_consistent(self):
        """assert-invariant：存進 DB 的 total 必須等於明細加總，對不上就擋。

        成交生訂單前跑一次——金額守恆是報價成交型的命門，破了不准往下走。
        """
        expected = sum((item.subtotal for item in self.items.all()), Decimal('0'))
        if self.total != expected:
            raise ValueError(f'金額守恆破了：total={self.total} ≠ Σ明細={expected}')

    # ── 狀態機 ─────────────────────────────────────────
    @property
    def is_editable(self):
        """能不能改明細（鐵則：已送出/終態鎖定）。"""
        return self.status in self.EDITABLE_STATUSES

    def available_actions(self):
        """目前狀態下「合法」的動作清單。給前端決定顯示哪些按鈕——
        但真相仍由 apply_transition() 再擋一次（前端只是體驗、後端才是牆）。"""
        return [action for action, t in self.TRANSITIONS.items() if self.status in t['from']]

    def apply_transition(self, action):
        """推進狀態機。非法轉移 → TransitionError（終態不可轉、跳步不可轉）。

        win（成交）是加碼的承重牆：生訂單前先 assert 金額守恆，再把凍結明細搬成一張訂單。
        （win 會多寫幾張表，呼叫端請包 transaction.atomic——見 apis.py。）
        """
        t = self.TRANSITIONS.get(action)
        if t is None:
            raise TransitionError(f'未知的動作：{action}')
        if self.status not in t['from']:
            allowed = '/'.join(self.Status(s).label for s in t['from'])
            raise TransitionError(
                f'「{self.get_status_display()}」不能{t["verb"]}（只有 {allowed} 可以）'
            )
        if action == 'win':
            self.assert_total_consistent()   # 金額守恆是成交的前提，破了不生訂單
            self.order = self._spawn_order()  # 承重牆：成交生訂單
        self.status = t['to']
        self.save(update_fields=['status', 'order', 'updated_at'])

    def _spawn_order(self):
        """成交生訂單：把報價當下凍結的明細（品名/單價快照）搬進一張新訂單。

        關鍵語意：用**報價的凍結價**成交，不重讀目錄現價——所以直接抄報價明細的
        name_snapshot/unit_price，而不是走 OrderItem.snapshot_from（那會抓現價）。
        局部 import 避免 order↔quotation 的載入期耦合（order 不認得 quotation）。
        """
        from apps.order.models import Order, OrderItem
        order = Order.objects.create(member=self.customer)
        for qi in self.items.all():
            OrderItem.objects.create(
                order=order,
                product=qi.product,
                name=qi.name,              # 報價當下的凍結品名
                unit_price=qi.unit_price,  # 報價當下的凍結單價（成交按報價）
                quantity=qi.quantity,
            )
        order.recalc_total()               # 訂單總額 = 明細加總（order 那邊的鐵則）
        return order


class QuotationItem(TimeStampedModel):
    """報價明細：報價當下抄商品的品名＋單價（快照），之後目錄變動不影響歷史。

    刻意跟 OrderItem 同形（classmethod 建立 + save 算小計），看完 order 這裡零學習成本。
    """

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    # 指回目錄（報表/追溯用）。PROTECT：被明細引用的商品不准硬刪（呼應「下架不刪」）。
    product = models.ForeignKey('product.Product', on_delete=models.PROTECT, related_name='quotation_items')
    name = models.CharField(max_length=100)                          # 品名（報價當下快照）
    quantity = models.PositiveIntegerField()                         # 數量（>0 由 schema 驗）
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # 單價（報價當下快照）
    # 小計不接受手填——save() 算出來存（鐵則入 code 的樣子，同 OrderItem）。
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    @classmethod
    def snapshot_from(cls, quotation, product, quantity):
        """報價當下：把目錄的品名＋單價「抄一份」存進明細（快照）。

        建立後改 product 的價格/名稱，這筆報價明細不受影響——歷史報價凍結。
        """
        return cls.objects.create(
            quotation=quotation,
            product=product,
            name=product.name,              # 快照
            unit_price=product.unit_price,  # 快照（product 的欄位叫 unit_price）
            quantity=quantity,
        )

    def save(self, *args, **kwargs):
        """鐵則：{明細小計 = 數量 × 單價}。錢的運算先轉 Decimal，不讓 float 參與（同 OrderItem）。"""
        self.subtotal = Decimal(self.quantity) * Decimal(str(self.unit_price))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} x{self.quantity}'
