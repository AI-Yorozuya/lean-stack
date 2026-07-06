"""seed_demo：灌入示範用的**會員 + 商品**，讓第一次起來就有東西看、門市有商品可逛。

**訂單不再 seed**——改由門市前台（lean-web）真實下單產生（登入 → 加購 → 結帳 → POST /order）。
這樣「客人下單 → 後台看到訂單」的 loop 是真的走一遍，不是灌假資料。

為什麼是「管理指令」而不是 fixture：規則長在 model（快照 / 加總 / 狀態機），走真 model 建才會發火。
冪等：已有商品就整個跳過（可安全每次開機跑；entrypoint 只在 DEBUG 灌）。要重灌先清資料。
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.member.models import Member
from apps.product.models import Product

# 會員：台灣風姓名＋email＋手機。email 是識別（一 email 一會員）。
# 第一筆是門市前台的「測試客」——lean-web 就登入這個帳號下單。
MEMBERS = [
    ('門市訪客', 'hero@ai-yorozuya.com', '0900-000-000'),
    ('陳雅婷', 'yating.chen@example.com', '0912-345-678'),
    ('林建宏', 'jianhong.lin@example.com', '0922-113-224'),
    ('黃淑芬', 'shufen.huang@example.com', '0933-556-778'),
    ('張家豪', 'jiahao.chang@example.com', '0955-778-990'),
    ('吳佩珊', 'peishan.wu@example.com', '0966-224-668'),
    ('劉俊傑', 'junjie.liu@example.com', '0988-336-996'),
    ('王思涵', 'sihan.wang@example.com', '0911-223-344'),
    ('蔡宗翰', 'zonghan.tsai@example.com', '0977-445-668'),
    ('鄭雅雯', 'yawen.cheng@example.com', '0933-889-221'),
    ('許志明', 'zhiming.hsu@example.com', '0955-667-889'),
    ('楊佳穎', 'jiaying.yang@example.com', '0966-778-990'),
]

# 服飾電商目錄：(sku, 品名, 牌價)。圖 = /products/<sku>.png（lean-web public/ 供）——
# 用 Medusa 官方 demo 的棚拍圖（乾淨白灰底、風格統一），所以目錄收斂成它涵蓋的這幾樣。
PRODUCTS = [
    ('TEE-WHITE', '經典素面 T 恤（白）', 590),
    ('TEE-BLACK', '經典素面 T 恤（黑）', 590),
    ('SWEAT', '復古大學 T', 1280),
    ('PANTS', '休閒棉質長褲', 1380),
    ('SHORTS', '復古休閒短褲', 880),
]


class Command(BaseCommand):
    help = '灌入示範會員＋商品（訂單改由門市前台真實下單）。冪等：已有商品就跳過。'

    @transaction.atomic
    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write('已有商品資料，seed_demo 跳過（冪等）。')
            return

        # 註冊 / 上架日期往回散開，讓那些日期欄有變化（created_at 是 auto_now_add，建完 update 回填）。
        now = timezone.now()

        # 會員：get_or_create 認 email。註冊日期散在過去約 40~280 天。
        for idx, (name, email, phone) in enumerate(MEMBERS):
            m, created = Member.objects.get_or_create(
                email=email, defaults={'name': name, 'phone': phone}
            )
            if created:
                reg = now - timedelta(days=280 - idx * 22)
                Member.objects.filter(pk=m.pk).update(created_at=reg, updated_at=reg)

        # 商品：get_or_create 認 sku。圖 = /products/<sku>.jpg。上架日期散在過去約 35~200 天。
        for idx, (sku, name, price) in enumerate(PRODUCTS):
            p, created = Product.objects.get_or_create(
                sku=sku,
                defaults={'name': name, 'unit_price': price, 'image_url': f'/products/{sku}.png'},
            )
            if created:
                listed = now - timedelta(days=200 - idx * 15)
                Product.objects.filter(pk=p.pk).update(created_at=listed, updated_at=listed)

        self.stdout.write(self.style.SUCCESS(
            f'seed_demo 完成：{len(MEMBERS)} 位會員、{len(PRODUCTS)} 個商品（訂單改由門市下單產生）。'
        ))
