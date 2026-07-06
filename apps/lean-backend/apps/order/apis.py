"""訂單管理的 API。規則來源：intents/訂單管理.md。

CRUD ＋ 關聯 ＋ 鐵則（把訂單建起來的部分）：
- 讀清單（帶條件、分頁）→ GET  /order
- 建立                  → POST /order
- 修改                  → PUT  /order/{id}
- 刪除                  → DELETE /order/{id}
（會員從 apps/member、商品從 apps/product 各自的端點取——這裡不重複。）

狀態機轉移端點（主戲：每個動作對應 INTENT 的一條合法轉移）：
- 收款 → POST /order/{id}/pay      （待付款 → 待出貨）
- 出貨 → POST /order/{id}/ship     （待出貨 → 已出貨）
- 取消 → POST /order/{id}/cancel   （待付款 / 待出貨 → 已取消）
非法轉移（終態不可轉、跳步不可轉）由 model 的 apply_transition 擋 → 422。

鐵則在門口與 model 兩層把關：
- {至少一筆明細}   → OrderIn 的 min_length=1（schemas.py）
- {明細=目錄快照}  → OrderItem.snapshot_from（models.py），本檔只給 product_id + qty
- {下架商品不可下單} → 本檔建單時擋（is_active）
- {小計=數量×單價} → OrderItem.save()（models.py）
- {總額=明細加總}  → 每次明細變動後 recalc_total()（本檔）
- {已出貨後不可改} → update_order 先查 is_editable（本檔）
- {合法轉移}       → Order.apply_transition（models.py）
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from apps.member.models import Member
from apps.order.models import Order, OrderItem, TransitionError
from apps.order.schemas import (
    MessageSchema,
    OrderIn,
    OrderListSchema,
    OrderNoteIn,
    OrderSchema,
)
from apps.product.models import Product

router = Router(tags=['order'])


def _add_items(order, items):
    """把 payload 的明細（product_id + quantity）建成訂單明細——各自抄目錄快照。

    下架商品不可下單（{下架=停售}）→ 422。品名/單價由 snapshot_from 從目錄抄，
    前端傳的價格一律不採信。
    """
    for item in items:
        product = get_object_or_404(Product, pk=item.product_id)
        if not product.is_active:
            raise HttpError(422, f'商品「{product.name}」已下架，不能下單')
        OrderItem.snapshot_from(order, product, item.quantity)


@transaction.atomic  # 訂單＋明細要嘛全存、要嘛全不存——不留「有單無明細」的半成品
def place_order(member, items):
    """把「一位會員 + 一批明細」做成一張訂單。**共用**：

    - 後台建單（create_order）：member 由前端傳的 member_id 撈；
    - 門市下單（apps/web）：member = 憑證裡的本人。

    差別只在「下單的人從哪來」；建單的鐵則（快照 / 小計 / 總額）全在這裡發火，一處真相。
    """
    order = Order.objects.create(member=member)
    _add_items(order, items)      # 各明細從目錄抄快照 + save() 算小計（鐵則）
    order.recalc_total()          # 鐵則：總額 = 明細加總
    return order


# ── 訂單 CRUD ────────────────────────────────────────────────
@router.get('', response=OrderListSchema)
def list_orders(request, page: int = 1, page_size: int = 10, q: str = '', member_id: int = None):
    """讀清單：q 模糊搜會員名，member_id 精準篩，page/page_size 分頁。

    對應前端元件：input（q）+ select（member_id）+ table + pagination。
    """
    qs = Order.objects.select_related('member').prefetch_related('items').order_by('-id')
    if q:
        qs = qs.filter(member__name__icontains=q)
    if member_id:
        qs = qs.filter(member_id=member_id)
    count = qs.count()
    start = (max(page, 1) - 1) * page_size
    return {'items': list(qs[start:start + page_size]), 'count': count}


@router.get('/{order_id}', response=OrderSchema)
def get_order(request, order_id: int):
    return get_object_or_404(
        Order.objects.select_related('member').prefetch_related('items'), pk=order_id
    )


@router.post('', response=OrderSchema)
def create_order(request, payload: OrderIn):
    """後台建單：下單的人由前端指定（member_id）——店員替客人建單。"""
    member = get_object_or_404(Member, pk=payload.member_id)
    return place_order(member, payload.items)


@router.put('/{order_id}', response=OrderSchema)
@transaction.atomic
def update_order(request, order_id: int, payload: OrderIn):
    """改單（會員與明細整組替換——最好懂的更新語意）。"""
    order = get_object_or_404(Order, pk=order_id)
    # 鐵則 {已出貨後明細/總額不可改}：生命週期的承重牆，砌在 update 入口。
    if not order.is_editable:
        raise HttpError(422, f'「{order.get_status_display()}」的訂單不可改明細（已出貨後鎖定）')
    order.member = get_object_or_404(Member, pk=payload.member_id)
    order.save(update_fields=['member', 'updated_at'])
    order.items.all().delete()
    _add_items(order, payload.items)
    order.recalc_total()
    return order


@router.delete('/{order_id}', response=MessageSchema)
def delete_order(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    order_no = order.order_no
    order.delete()  # 明細跟著刪（models 的 on_delete=CASCADE）
    return {'message': f'訂單 {order_no} 已刪除'}


@router.post('/{order_id}/note', response=OrderSchema)
def update_order_note(request, order_id: int, payload: OrderNoteIn):
    """只改備註（自由文字，跟狀態無關；前端備註欄 inline dialog 用）。"""
    order = get_object_or_404(
        Order.objects.select_related('member').prefetch_related('items'), pk=order_id
    )
    order.note = payload.note
    order.save(update_fields=['note', 'updated_at'])
    return order


# ── 訂單狀態機：一個動作一個端點，都走 model 的 apply_transition ──
# 非法轉移由 model 擋（TransitionError）→ 這裡統一轉成 422 給前端顯示白話原因。
def _transition(order_id, action):
    order = get_object_or_404(
        Order.objects.select_related('member').prefetch_related('items'), pk=order_id
    )
    try:
        order.apply_transition(action)
    except TransitionError as e:
        raise HttpError(422, str(e))
    return order


@router.post('/{order_id}/pay', response=OrderSchema)
def pay_order(request, order_id: int):
    """收款：待付款 → 待出貨（[收款金額 = 總額]，鎖 paid_amount）。"""
    return _transition(order_id, 'pay')


@router.post('/{order_id}/ship', response=OrderSchema)
def ship_order(request, order_id: int):
    """出貨：待出貨 → 已出貨（終態·成功；出貨後明細鎖定）。"""
    return _transition(order_id, 'ship')


@router.post('/{order_id}/cancel', response=OrderSchema)
def cancel_order(request, order_id: int):
    """取消：待付款 / 待出貨 → 已取消（終態；出貨後不可取消）。"""
    return _transition(order_id, 'cancel')
