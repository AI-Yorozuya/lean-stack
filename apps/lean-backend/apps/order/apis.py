"""訂單管理 Stage A 的 API：無狀態 CRUD ＋ 關聯 ＋ 鐵則。

教學重點（這一頁 API 對應「認識積木」列表頁的四個動作）：
- 讀清單（帶條件、分頁）→ GET  /order
- 建立                  → POST /order
- 修改                  → PUT  /order/{id}
- 刪除                  → DELETE /order/{id}
外加客戶的最小讀/建（給下單表單的 select 用）。

鐵則在門口與 model 兩層把關：
- {至少一筆明細}  → OrderIn 的 min_length=1（schemas.py）
- {小計=數量×單價} → OrderItem.save()（models.py）
- {總額=明細加總}  → 每次明細變動後 recalc_total()（本檔）
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.order.models import Customer, Order, OrderItem
from apps.order.schemas import (
    CustomerIn,
    CustomerSchema,
    MessageSchema,
    OrderIn,
    OrderListSchema,
    OrderSchema,
)

router = Router(tags=['order'])


# ── 客戶（最小：列表 + 建立，給下單表單用）───────────────────
@router.get('/customers', response=list[CustomerSchema])
def list_customers(request):
    return Customer.objects.order_by('name')


@router.post('/customers', response=CustomerSchema)
def create_customer(request, payload: CustomerIn):
    return Customer.objects.create(**payload.dict())


# ── 訂單 CRUD ────────────────────────────────────────────────
@router.get('', response=OrderListSchema)
def list_orders(request, page: int = 1, page_size: int = 10, q: str = '', customer_id: int = None):
    """讀清單：q 模糊搜客戶名，customer_id 精準篩，page/page_size 分頁。

    對應前端元件：input（q）+ select（customer_id）+ table + pagination。
    """
    qs = Order.objects.select_related('customer').prefetch_related('items').order_by('-id')
    if q:
        qs = qs.filter(customer__name__icontains=q)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    count = qs.count()
    start = (max(page, 1) - 1) * page_size
    return {'items': list(qs[start:start + page_size]), 'count': count}


@router.get('/{order_id}', response=OrderSchema)
def get_order(request, order_id: int):
    return get_object_or_404(
        Order.objects.select_related('customer').prefetch_related('items'), pk=order_id
    )


@router.post('', response=OrderSchema)
@transaction.atomic  # 訂單＋明細要嘛全存、要嘛全不存——不留「有單無明細」的半成品
def create_order(request, payload: OrderIn):
    customer = get_object_or_404(Customer, pk=payload.customer_id)
    order = Order.objects.create(customer=customer)
    for item in payload.items:
        OrderItem.objects.create(order=order, **item.dict())  # save() 會算小計（鐵則）
    order.recalc_total()  # 鐵則：總額 = 明細加總
    return order


@router.put('/{order_id}', response=OrderSchema)
@transaction.atomic
def update_order(request, order_id: int, payload: OrderIn):
    """改單（Stage A：客戶與明細整組替換——最好懂的更新語意）。"""
    order = get_object_or_404(Order, pk=order_id)
    order.customer = get_object_or_404(Customer, pk=payload.customer_id)
    order.save(update_fields=['customer', 'updated_at'])
    order.items.all().delete()
    for item in payload.items:
        OrderItem.objects.create(order=order, **item.dict())
    order.recalc_total()
    return order


@router.delete('/{order_id}', response=MessageSchema)
def delete_order(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    order.delete()  # 明細跟著刪（models 的 on_delete=CASCADE）
    return {'message': f'訂單 #{order_id} 已刪除'}
