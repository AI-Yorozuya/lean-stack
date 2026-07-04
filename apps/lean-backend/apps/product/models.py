"""商品目錄模型。規則來源：intents/商品管理.md。

教學重點：跟會員一樣是**最單純的 CRUD**，但它扮演一個關鍵角色——
**品名與價格的「單一真相」**。訂單明細在下單當下從這裡「抄一份快照」
（見 apps/order/models.py 的 OrderItem.snapshot_from），之後改這裡不動歷史訂單。

- {一個 sku 只能對到一個商品} → sku unique。
- {下架 = 停售不刪}           → is_active，永不 DELETE；被明細引用時 PROTECT 擋刪。
"""
from django.db import models

from apps._common.models import TimeStampedModel


class Product(TimeStampedModel):
    sku = models.CharField(max_length=40, unique=True)   # 鐵則 {一 sku 一商品}
    name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # 牌價（現價）
    # 下架不是刪——關掉 is_active 就不能再被下單，但歷史明細仍指得到。
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.sku} {self.name}'
