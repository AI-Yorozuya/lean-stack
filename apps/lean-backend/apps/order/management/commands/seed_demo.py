"""seed_demo：一鍵灌入擬真的示範資料（會員＋商品＋訂單），讓第一次起來就有東西看。

為什麼是「管理指令」而不是 fixture？
  這 repo 的規則長在 model：OrderItem.save() 算小計、snapshot_from 抄目錄快照、
  recalc_total() 加總、apply_transition() 推狀態機（見各 app 的 models.py）。而 Django
  的 loaddata（fixture）會用 raw=True 跳過 save()——等於要手工焊死 subtotal/total/快照，
  跟規則靜靜地對不上。走指令、經真 model 建，鐵則會「真的發火」，順便就是活的 demo。

冪等：已經有任何訂單就整個跳過，所以可以安全地每次開機都跑（entrypoint.sh 只在
  DEBUG 灌）。要重灌：先清資料再跑。

資料串起三個 app：會員（下單的人）＋商品目錄（單一真相）→ 訂單從目錄挑、抄快照。
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.member.models import Member
from apps.order.models import Order, OrderItem
from apps.product.models import Product

# 會員（萬事屋的客人）：台灣風姓名＋email＋手機。email 是識別（一 email 一會員）。
MEMBERS = [
    ('陳雅婷', 'yating.chen@example.com', '0912-345-678'),
    ('林建宏', 'jianhong.lin@example.com', '0922-113-224'),
    ('黃淑芬', 'shufen.huang@example.com', '0933-556-778'),
    ('張家豪', 'jiahao.chang@example.com', '0955-778-990'),
    ('吳佩珊', 'peishan.wu@example.com', '0966-224-668'),
    ('劉俊傑', 'junjie.liu@example.com', '0988-336-996'),
]

# 商品／服務目錄：(sku, 品名, 牌價)。訂單明細下單當下從這裡抄快照。
PRODUCTS = [
    ('SVC-CLEAN', '居家深度打掃', 1800),
    ('SVC-AC', '冷氣清洗', 1600),
    ('SVC-MOVE', '搬家協助（小型）', 2500),
    ('SVC-PET', '寵物到府代顧（日）', 800),
    ('SVC-GIFT', '代購伴手禮', 450),
    ('SVC-PC', '電腦重灌與檢測', 1200),
    ('SVC-FIX', '水電小修', 900),
    ('SVC-TUTOR', '到府家教（時）', 700),
    ('SVC-QUEUE', '代客排隊購物', 600),
    ('SVC-FLOWER', '花藝代送', 550),
]

# 一張訂單的藍圖：(會員 index, [(商品 sku, 數量)…], 要推到哪個狀態)。
ORDERS = [
    (0, [('SVC-CLEAN', 1), ('SVC-AC', 2)], 'COMPLETED'),
    (1, [('SVC-MOVE', 1)], 'SHIPPED'),
    (2, [('SVC-PET', 3), ('SVC-GIFT', 2)], 'PAID'),
    (3, [('SVC-PC', 1), ('SVC-FIX', 1)], 'PENDING'),
    (4, [('SVC-TUTOR', 4)], 'COMPLETED'),
    (5, [('SVC-QUEUE', 2), ('SVC-FLOWER', 1)], 'REFUNDED'),
    (0, [('SVC-AC', 1)], 'PENDING'),
    (2, [('SVC-CLEAN', 1), ('SVC-FIX', 2), ('SVC-GIFT', 1)], 'PAID'),
]

# 推到某狀態要走的動作序列——全走真狀態機 apply_transition()，不硬塞 status。
# 鋪出「待付款～已退款」整條生命週期，清單頁和狀態頁都活起來。
PATH_TO = {
    'PENDING':   [],
    'PAID':      ['pay'],
    'SHIPPED':   ['pay', 'ship'],
    'COMPLETED': ['pay', 'ship', 'complete'],
    'REFUNDED':  ['pay', 'ship', 'refund'],
}


class Command(BaseCommand):
    help = '灌入擬真示範資料（會員＋商品＋訂單）。冪等：已有訂單就跳過。'

    @transaction.atomic
    def handle(self, *args, **options):
        if Order.objects.exists():
            self.stdout.write('已有訂單資料，seed_demo 跳過（冪等）。')
            return

        # 會員：get_or_create 認 email（一 email 一會員），防重跑長重複。
        members = []
        for name, email, phone in MEMBERS:
            m, _ = Member.objects.get_or_create(
                email=email, defaults={'name': name, 'phone': phone}
            )
            members.append(m)

        # 商品目錄：get_or_create 認 sku（一 sku 一商品）。
        catalog = {}
        for sku, name, price in PRODUCTS:
            p, _ = Product.objects.get_or_create(
                sku=sku, defaults={'name': name, 'unit_price': price}
            )
            catalog[sku] = p

        for member_idx, lines, target in ORDERS:
            order = Order.objects.create(member=members[member_idx])
            for sku, qty in lines:
                # 經真 model：從目錄抄品名＋單價快照，save() 再算 subtotal（鐵則發火）。
                OrderItem.snapshot_from(order, catalog[sku], qty)
            order.recalc_total()                    # 鐵則：總額 = 明細加總
            for action in PATH_TO[target]:
                order.apply_transition(action)      # 走真狀態機推進生命週期

        self.stdout.write(self.style.SUCCESS(
            f'seed_demo 完成：{len(members)} 位會員、{len(catalog)} 個商品、{len(ORDERS)} 筆訂單。'
        ))
