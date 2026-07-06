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

# 會員：只灌**一位**——門市前台的「測試客」。lean-web 就登入這個帳號下單。
# 刻意不灌一堆假會員：會員頁在教學裡是「最單純讀清單」，一位真人夠示範；
# 名單要長起來，是靠門市之後真的有人來（後端補上註冊/登入才會長）。
MEMBERS = [
    ('門市訪客', 'hero@ai-yorozuya.com', '0900-000-000'),
]

# 測試客的示範密碼：門市登入頁已幫她預填好，一鍵登入。
# 存進 DB 的是**雜湊**（Member.set_password），不是這串明文。
DEMO_PASSWORD = '12345678'

# 服飾電商目錄：(sku, 品名, 牌價)。圖 = /products/<sku>.png（lean-web public/ 供）。
# 底圖用 Medusa 官方 demo 棚拍照，再用「保留光影、換飽和色 + 遮罩留白」生出各色——
# 所以 12 樣同一套棚拍風格、顏色卻真的各異（不是同張照片重貼）。
PRODUCTS = [
    ('TEE-WHITE', '經典素面 T 恤 · 白', 590),
    ('TEE-BLACK', '經典素面 T 恤 · 黑', 590),
    ('SWEAT-WINE', '復古大學 T · 酒紅', 1280),
    ('SWEAT-NAVY', '復古大學 T · 海軍藍', 1280),
    ('SWEAT-MUSTARD', '復古大學 T · 芥末黃', 1280),
    ('SWEAT-FOREST', '復古大學 T · 森林綠', 1280),
    ('SHORTS-BRICK', '休閒短褲 · 磚紅', 880),
    ('SHORTS-OLIVE', '休閒短褲 · 橄欖綠', 880),
    ('SHORTS-NAVY', '休閒短褲 · 海軍藍', 880),
    ('SHORTS-KHAKI', '休閒短褲 · 卡其', 880),
    ('PANTS-KHAKI', '休閒棉褲 · 卡其', 1380),
    ('PANTS-CHARCOAL', '休閒棉褲 · 炭灰', 1380),
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

        # 會員：get_or_create 認 email。測試客的註冊日期設在過去約半年前。
        for idx, (name, email, phone) in enumerate(MEMBERS):
            m, created = Member.objects.get_or_create(
                email=email, defaults={'name': name, 'phone': phone}
            )
            if created:
                m.set_password(DEMO_PASSWORD)   # 設示範密碼（存雜湊），門市才登得進來
                m.save(update_fields=['password'])
                reg = now - timedelta(days=180)
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
