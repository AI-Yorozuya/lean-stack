"""訂單管理 Stage A 的資料模型。規則來源：intents/訂單管理.md（Stage A）。

教學重點（資料模型＝三問的第一問「有什麼？跟誰有關？」）：
- 三個「東西」：客戶 Customer、訂單 Order、訂單明細 OrderItem。
- 兩條關聯：訂單 → 客戶（多對一）；明細 → 訂單（多對一，也就是訂單:明細 = 1:N）。
- Stage A 刻意「無狀態機」——訂單就是一筆有明細、有客戶的資料。
  生命週期（待付款→已付款→…）是 Stage B 的事。

鐵則（intents 裡的 {…}）落在哪：
- {明細小計 = 數量 × 單價}   → OrderItem.save() 裡「算出來存」，不接受手填。
- {訂單總額 = 明細加總}      → Order.recalc_total()，任何明細變動後由 API 層呼叫。
- {一張訂單至少一筆明細}     → 建立/修改的入口（apis.py）擋，見該檔。

為什麼鐵則寫在 model / 入口，而不是「相信前端」？
前端畫面可以算給人看（體驗），但**真相必須由後端算**——不然改個明細、
總額沒跟上，帳就錯了。這正是「demo 會動 ≠ 能上線」最小的例子。
"""
from decimal import Decimal

from django.db import models

from apps._common.models import TimeStampedModel


class Customer(TimeStampedModel):
    """下單的人。Stage A 用最簡客戶表（之後可換成接會員 app）。"""

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.name


class Order(TimeStampedModel):
    """一次銷售。Stage A：沒有狀態欄位（刻意），只有客戶、日期、總額。"""

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,  # 有訂單的客戶不准刪——歷史要留（呼應「停用不刪」的精神）
        related_name='orders',
    )
    order_date = models.DateField(auto_now_add=True)
    # 總額永遠是「算出來的」（recalc_total），欄位只是快取查詢方便。
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))

    def __str__(self):
        return f'Order#{self.pk} {self.customer} ${self.total}'

    def recalc_total(self):
        """鐵則：{訂單總額 = 所有明細小計加總}。明細有任何增刪改後呼叫。"""
        self.total = sum((item.subtotal for item in self.items.all()), Decimal('0'))
        self.save(update_fields=['total', 'updated_at'])


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
