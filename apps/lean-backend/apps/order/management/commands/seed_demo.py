"""seed_demo：灌入示範用的**客戶 + 產品**，讓第一次起來就有東西看、報價單有客戶與產品可挑。

**訂單不 seed**——訂單由「報價成交」真實產生（報價單 → 送出 → 成交 → 自動生訂單）。
這樣「談成一張報價 → 後台生出訂單」的 loop 是真的走一遍，不是灌假資料。

為什麼是「管理指令」而不是 fixture：規則長在 model（快照 / 加總 / 狀態機），走真 model 建才會發火。
冪等：已有產品就整個跳過（可安全每次開機跑；entrypoint 只在 DEBUG 灌）。要重灌先清資料。
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.member.models import Member
from apps.product.models import Product

# 客戶：報價成交型的「客戶」抽象槽（宿主是 Member）。灌幾家 B2B 企業客戶當示範，
# 報價單就有對象可挑。名單要長起來，靠之後真的接到案子（新客戶隨業務建）。
CUSTOMERS = [
    ('大山工程行', 'dashan@demo.co', '0912-345-678'),
    ('宏昇系統整合', 'hongsheng@demo.co', '0922-111-222'),
    ('綠川室內設計', 'lyuchuan@demo.co', '0933-444-555'),
    ('台興機械', 'taixing@demo.co', '0955-666-777'),
]

# 產品目錄：(sku, 品名, 單價)。以「辦公設備供應商」當示範業種——
# 報價成交型很典型：客戶問價 → 出報價 → 談成生訂單。品項具體、單價好懂。
PRODUCTS = [
    ('DESK-SOLID', '實木辦公桌', 8500),
    ('CHAIR-ERGO', '人體工學椅', 4200),
    ('CABINET-STEEL', '鋼製資料櫃', 3600),
    ('TABLE-MEET6', '六人會議桌', 12800),
    ('WHITEBOARD-L', '大型白板', 1800),
    ('PROJECTOR-HD', '高畫質投影機', 15600),
    ('SWITCH-24P', '24 埠網路交換器', 5400),
    ('RACK-SERVER', '伺服器機櫃', 9800),
    ('LAMP-LED', 'LED 護眼檯燈', 990),
    ('SOFA-GUEST', '訪客沙發組', 18500),
]


class Command(BaseCommand):
    help = '灌入示範客戶＋產品（訂單改由報價成交產生）。冪等：已有產品就跳過。'

    @transaction.atomic
    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write('已有產品資料，seed_demo 跳過（冪等）。')
            return

        # 建立日期往回散開，讓那些日期欄有變化（created_at 是 auto_now_add，建完 update 回填）。
        now = timezone.now()

        # 客戶：get_or_create 認 email，建立日期散在過去約半年內。
        for idx, (name, email, phone) in enumerate(CUSTOMERS):
            m, created = Member.objects.get_or_create(
                email=email, defaults={'name': name, 'phone': phone}
            )
            if created:
                reg = now - timedelta(days=180 - idx * 30)
                Member.objects.filter(pk=m.pk).update(created_at=reg, updated_at=reg)

        # 產品：get_or_create 認 sku。建立日期散在過去約 35~200 天。
        for idx, (sku, name, price) in enumerate(PRODUCTS):
            p, created = Product.objects.get_or_create(
                sku=sku,
                defaults={'name': name, 'unit_price': price},
            )
            if created:
                listed = now - timedelta(days=200 - idx * 15)
                Product.objects.filter(pk=p.pk).update(created_at=listed, updated_at=listed)

        self.stdout.write(self.style.SUCCESS(
            f'seed_demo 完成：{len(CUSTOMERS)} 位客戶、{len(PRODUCTS)} 個產品（訂單改由報價成交產生）。'
        ))
