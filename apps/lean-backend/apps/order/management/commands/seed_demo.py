"""seed_demo：一鍵灌入擬真的示範資料（會員＋訂單），讓第一次起來就有東西看。

為什麼是「管理指令」而不是 fixture？
  這 repo 的規則長在 model：OrderItem.save() 算小計、Order.recalc_total() 加總、
  apply_transition() 推狀態機（見 apps/order/models.py）。而 Django 的 loaddata
  （fixture）會用 raw=True 跳過 save()——等於要手工焊死 subtotal/total/paid_amount，
  跟規則靜靜地對不上。走指令、經真 model 建，鐵則會「真的發火」，順便就是活的 demo。

冪等：已經有任何訂單就整個跳過，所以可以安全地每次開機都跑（entrypoint.sh 只在
  DEBUG 灌）。要重灌：先清資料（flush / 刪訂單）再跑。

會員？這 sandbox 還沒有獨立會員 app，照 Customer 的註解拿它當「下單的人／會員」。
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.order.models import Customer, Order, OrderItem

# 會員（萬事屋的客人）：台灣風姓名＋手機。get_or_create 認 name，重跑不長重複。
CUSTOMERS = [
    ('陳雅婷', '0912-345-678'),
    ('林建宏', '0922-113-224'),
    ('黃淑芬', '0933-556-778'),
    ('張家豪', '0955-778-990'),
    ('吳佩珊', '0966-224-668'),
    ('劉俊傑', '0988-336-996'),
]

# 萬事屋服務品項的單價表（元）。
PRICES = {
    '居家深度打掃': 1800,
    '冷氣清洗': 1600,
    '搬家協助（小型）': 2500,
    '寵物到府代顧（日）': 800,
    '代購伴手禮': 450,
    '電腦重灌與檢測': 1200,
    '水電小修': 900,
    '到府家教（時）': 700,
    '代客排隊購物': 600,
    '花藝代送': 550,
}

# 一張訂單的藍圖：(客人 index, [(品項, 數量)…], 要推到哪個狀態)。
ORDERS = [
    (0, [('居家深度打掃', 1), ('冷氣清洗', 2)], 'COMPLETED'),
    (1, [('搬家協助（小型）', 1)], 'SHIPPED'),
    (2, [('寵物到府代顧（日）', 3), ('代購伴手禮', 2)], 'PAID'),
    (3, [('電腦重灌與檢測', 1), ('水電小修', 1)], 'PENDING'),
    (4, [('到府家教（時）', 4)], 'COMPLETED'),
    (5, [('代客排隊購物', 2), ('花藝代送', 1)], 'REFUNDED'),
    (0, [('冷氣清洗', 1)], 'PENDING'),
    (2, [('居家深度打掃', 1), ('水電小修', 2), ('代購伴手禮', 1)], 'PAID'),
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
    help = '灌入擬真示範資料（會員＋訂單）。冪等：已有訂單就跳過。'

    @transaction.atomic
    def handle(self, *args, **options):
        if Order.objects.exists():
            self.stdout.write('已有訂單資料，seed_demo 跳過（冪等）。')
            return

        # 會員：get_or_create 防重跑長重複。
        customers = []
        for name, phone in CUSTOMERS:
            c, _ = Customer.objects.get_or_create(name=name, defaults={'phone': phone})
            customers.append(c)

        for cust_idx, items, target in ORDERS:
            order = Order.objects.create(customer=customers[cust_idx])
            for item_name, qty in items:
                # 經真 model：OrderItem.save() 會算 subtotal（鐵則發火）。
                OrderItem.objects.create(
                    order=order,
                    name=item_name,
                    quantity=qty,
                    unit_price=Decimal(PRICES[item_name]),
                )
            order.recalc_total()                    # 鐵則：總額 = 明細加總
            for action in PATH_TO[target]:
                order.apply_transition(action)      # 走真狀態機推進生命週期

        self.stdout.write(self.style.SUCCESS(
            f'seed_demo 完成：{len(customers)} 位會員、{len(ORDERS)} 筆訂單。'
        ))
