"""客戶資料模型。規則來源：intents/會員管理.md。

教學重點：**最單純的 CRUD model**——示範「連近乎無狀態的東西也有鐵則」。
- {一個 email 只能對到一個客戶}  → email unique（DB 層擋，撞了 API 轉 422）。
- {停用 = 關閉，不刪}            → status 啟用/停用，永不 DELETE。

客戶就是「開單的人」：訂單的 Order.member 外鍵指向這裡（見 apps/order/models.py）。
不另捏客戶表——同一個「人」只有一個真相。
"""
from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from apps._common.models import TimeStampedModel


class Member(TimeStampedModel):
    class Status(models.TextChoices):
        # value（存 DB / 走 API）, label（給人看的中文）
        ACTIVE = 'ACTIVE', '啟用'
        INACTIVE = 'INACTIVE', '停用'

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)   # 鐵則 {一 email 一客戶}
    phone = models.CharField(max_length=30, blank=True)
    # 停用不是刪——用狀態欄關閉，歷史（含他開過的訂單）都留得住。
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    # 登入密碼：**永遠存雜湊、不存明文**（set_password 用 Django 內建 PBKDF2 雜湊）。
    # 空字串 = 還沒設密碼（不能登入）。真驗密碼的登入端點見 apps/member/apis.py。
    password = models.CharField(max_length=128, blank=True)

    def set_password(self, raw_password):
        """設定密碼：存的是雜湊，不是明文。"""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """核對密碼：拿明文跟存的雜湊比。沒設過密碼一律不通過。"""
        return bool(self.password) and check_password(raw_password, self.password)

    def __str__(self):
        return self.name
