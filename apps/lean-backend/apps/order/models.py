"""訂單管理的資料模型。規則來源：intents/訂單管理.md（Stage A + Stage B）。

教學重點（資料模型＝三問的第一問「有什麼？跟誰有關？」）：
- 三個「東西」：客戶 Customer、訂單 Order、訂單明細 OrderItem。
- 兩條關聯：訂單 → 客戶（多對一）；明細 → 訂單（多對一，也就是訂單:明細 = 1:N）。
- Stage A（無狀態）：訂單就是一筆有明細、有客戶的資料，只有 CRUD。
- Stage B（有狀態）：**同一個 Order 加上生命週期**——status 狀態機 + 更多鐵則。

鐵則（intents 裡的 {…}）落在哪：
- {明細小計 = 數量 × 單價}   → OrderItem.save() 裡「算出來存」，不接受手填。
- {訂單總額 = 明細加總}      → Order.recalc_total()，任何明細變動後由 API 層呼叫。
- {一張訂單至少一筆明細}     → 建立/修改的入口（apis.py）擋，見該檔。
- {已出貨後明細/總額不可改} → Order.is_editable（EDITABLE_STATUSES），update 入口擋。
- {終態不可再轉}/{跳步不可轉} → Order.apply_transition() 用 TRANSITIONS 表守。

為什麼鐵則寫在 model / 入口，而不是「相信前端」？
前端畫面可以算給人看（體驗），但**真相必須由後端算/擋**——狀態機的「哪條路
不能走」若只靠前端藏按鈕，改個 request 就破功。承重牆砌在後端才擋得住。
"""
from decimal import Decimal

from django.db import models

from apps._common.models import TimeStampedModel


class TransitionError(Exception):
    """狀態機擋下來的「非法轉移」（終態不可轉、跳步不可轉）。API 層轉成 422。"""


class Customer(TimeStampedModel):
    """下單的人。Stage A 用最簡客戶表（之後可換成接會員 app）。"""

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.name


class Order(TimeStampedModel):
    """一次銷售。Stage A 用 CRUD；Stage B 加上 status 生命週期（狀態機）。"""

    class Status(models.TextChoices):
        # value（存 DB / 走 API）  , label（給人看的中文）
        PENDING = 'PENDING', '待付款'
        PAID = 'PAID', '已付款'
        SHIPPED = 'SHIPPED', '已出貨'
        COMPLETED = 'COMPLETED', '已完成'
        REFUNDED = 'REFUNDED', '已退款'

    # ── 狀態機的「真相」：合法轉移表。action → 從哪些狀態、轉去哪、動詞。──
    # 沒列在這裡的 (狀態, 動作) 組合＝非法（含終態不可轉、跳步不可轉）。
    TRANSITIONS = {
        'pay':      {'from': (Status.PENDING,),               'to': Status.PAID,      'verb': '收款'},
        'ship':     {'from': (Status.PAID,),                  'to': Status.SHIPPED,   'verb': '出貨'},
        'complete': {'from': (Status.SHIPPED,),               'to': Status.COMPLETED, 'verb': '完成'},
        'refund':   {'from': (Status.PAID, Status.SHIPPED),   'to': Status.REFUNDED,  'verb': '退款'},
    }
    # 鐵則 {已出貨後明細/總額不可改}：只有這兩個狀態能動明細。
    EDITABLE_STATUSES = (Status.PENDING, Status.PAID)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,  # 有訂單的客戶不准刪——歷史要留（呼應「停用不刪」的精神）
        related_name='orders',
    )
    order_date = models.DateField(auto_now_add=True)
    # 總額永遠是「算出來的」（recalc_total），欄位只是快取查詢方便。
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    # Stage B：生命週期狀態（預設待付款）＋ 已收金額（收款時鎖成總額）。
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    def __str__(self):
        return f'Order#{self.pk} {self.customer} ${self.total} [{self.get_status_display()}]'

    def recalc_total(self):
        """鐵則：{訂單總額 = 所有明細小計加總}。明細有任何增刪改後呼叫。"""
        self.total = sum((item.subtotal for item in self.items.all()), Decimal('0'))
        self.save(update_fields=['total', 'updated_at'])

    # ── Stage B：狀態機 ─────────────────────────────────────────
    @property
    def is_editable(self):
        """能不能改明細（鐵則：已出貨/終態鎖定）。"""
        return self.status in self.EDITABLE_STATUSES

    def available_actions(self):
        """目前狀態下「合法」的動作清單。給前端決定顯示哪些按鈕——
        但真相仍由 apply_transition() 再擋一次（前端只是體驗、後端才是牆）。"""
        return [action for action, t in self.TRANSITIONS.items() if self.status in t['from']]

    def apply_transition(self, action):
        """推進狀態機。非法轉移 → TransitionError（終態不可轉、跳步不可轉）。"""
        t = self.TRANSITIONS.get(action)
        if t is None:
            raise TransitionError(f'未知的動作：{action}')
        if self.status not in t['from']:
            allowed = '/'.join(self.Status(s).label for s in t['from'])
            raise TransitionError(
                f'「{self.get_status_display()}」不能{t["verb"]}（只有 {allowed} 可以）'
            )
        if action == 'pay':
            self.paid_amount = self.total   # [收款金額 = 總額]
        # 退款：INTENT park 了部分/多次退款 → 做全額單次退，
        # 退款額 = paid_amount ≤ paid_amount，鐵則 {退款 ≤ 已付} 恆成立。
        self.status = t['to']
        self.save(update_fields=['status', 'paid_amount', 'updated_at'])


class OrderItem(TimeStampedModel):
    """訂單裡的一個品項。訂單:明細 = 1:N。"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)                          # 品項名
    quantity = models.PositiveIntegerField()                         # 數量（>0 由 schema 驗）
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # 單價
    # 小計不接受手填——save() 算出來存（鐵則入 code 的樣子）。
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        """鐵則：{明細小計 = 數量 × 單價}。不管誰存、怎麼存，這條永遠成立。

        Decimal(str(...))：不管上游塞進來的是 int / float / str / Decimal，
        先安全轉成 Decimal 再算——錢的運算永遠不讓 float 參與（會有二進位誤差）。
        """
        self.subtotal = Decimal(self.quantity) * Decimal(str(self.unit_price))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} x{self.quantity}'
