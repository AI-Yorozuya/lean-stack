"""訂單管理的 API。規則來源：intents/訂單管理.md。

CRUD ＋ 關聯 ＋ 鐵則（把訂單建起來的部分）：
- 讀清單（帶條件、分頁）→ GET  /order
- 建立                  → POST /order
- 修改                  → PUT  /order/{id}
- 刪除                  → DELETE /order/{id}
（客戶從 apps/member、產品從 apps/product 各自的端點取——這裡不重複。）

狀態機轉移端點（主戲：每個動作對應 INTENT 的一條合法轉移）：
- 收款 → POST /order/{id}/pay      （待付款 → 待出貨）
- 出貨 → POST /order/{id}/ship     （待出貨 → 已出貨）
- 取消 → POST /order/{id}/cancel   （待付款 / 待出貨 → 已取消）
非法轉移（終態不可轉、跳步不可轉）由 model 的 apply_transition 擋 → 422。

鐵則在門口與 model 兩層把關：
- {至少一筆明細}   → OrderIn 的 min_length=1（schemas.py）
- {明細=目錄快照}  → OrderItem.snapshot_from（models.py），本檔只給 product_id + qty
- {停售產品不可建單} → 本檔建單時擋（is_active）
- {小計=數量×單價} → OrderItem.save()（models.py）
- {總額=明細加總}  → 每次明細變動後 recalc_total()（本檔）
- {已出貨後不可改} → update_order 先查 is_editable（本檔）
- {合法轉移}       → Order.apply_transition（models.py）
"""
from django.db import transaction
from django.db.models import Count, Q
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

    停售產品不可建單 → 422。品名/單價由 snapshot_from 從目錄抄，
    前端傳的價格一律不採信。
    """
    for item in items:
        product = get_object_or_404(Product, pk=item.product_id)
        if not product.is_active:
            raise HttpError(422, f'產品「{product.name}」已停售，不能建單')
        OrderItem.snapshot_from(order, product, item.quantity)


@transaction.atomic  # 訂單＋明細要嘛全存、要嘛全不存——不留「有單無明細」的半成品
def place_order(member, items):
    """把「一位客戶 + 一批明細」做成一張訂單。**共用**：

    - 後台建單（create_order）：member 由前端傳的 member_id 撈；
    - 報價成交生訂單：member = 報價單上的客戶。

    差別只在「建單的人從哪來」；建單的鐵則（快照 / 小計 / 總額）全在這裡發火，一處真相。
    """
    order = Order.objects.create(member=member)
    _add_items(order, items)      # 各明細從目錄抄快照 + save() 算小計（鐵則）
    order.recalc_total()          # 鐵則：總額 = 明細加總
    order.post_initial_charge()   # 帳款連動：建單即開一筆應收（見 apps/billing）
    return order


# ── 訂單 CRUD ────────────────────────────────────────────────
@router.get('', response=OrderListSchema)
def list_orders(request, page: int = 1, page_size: int = 10, search: str = '', status: str = '', member_id: int = None):
    """讀清單——**後端完整篩選**：status 篩狀態、search 模糊搜(客戶名/單號)、member_id 精準、page/page_size 分頁。

    頁面上每個控制項都是一個 query 參數，後端一次 filter 完只回那一頁——不是抓全部前端再篩。
    對應前端元件：狀態頁籤(status) + 搜尋框(search) + 分頁(page/page_size) + select(member_id)。
    status_counts：各狀態的筆數（在 search 篩選後、status 篩選前算），給狀態頁籤的計數。
    """
    qs = Order.objects.select_related('member').prefetch_related('items').order_by('-id')
    if search:
        qs = qs.filter(Q(member__name__icontains=search) | Q(order_no__icontains=search))
    if member_id:
        qs = qs.filter(member_id=member_id)
    # .order_by() 清掉預設 -id 排序，否則會混進 GROUP BY 讓聚合拆成一筆一組
    by_status = {r['status']: r['n'] for r in qs.order_by().values('status').annotate(n=Count('id'))}
    status_counts = {'all': sum(by_status.values()),
                     **{s: by_status.get(s, 0) for s, _ in Order.Status.choices}}
    if status and status != 'all':
        qs = qs.filter(status=status)
    count = qs.count()
    start = (max(page, 1) - 1) * page_size
    return {'items': list(qs[start:start + page_size]), 'count': count, 'status_counts': status_counts}


@router.get('/{order_id}', response=OrderSchema)
def get_order(request, order_id: int):
    return get_object_or_404(
        Order.objects.select_related('member').prefetch_related('items'), pk=order_id
    )


@router.post('', response=OrderSchema)
def create_order(request, payload: OrderIn):
    """後台建單：建單的人由前端指定（member_id）——店員替客戶建單。"""
    member = get_object_or_404(Member, pk=payload.member_id)
    return place_order(member, payload.items)


@router.put('/{order_id}', response=OrderSchema)
@transaction.atomic
def update_order(request, order_id: int, payload: OrderIn):
    """改單（客戶與明細整組替換——最好懂的更新語意）。"""
    # select_for_update：鎖住這張訂單，序列化並發改單/收款（否則兩個請求可能各記一次調整）。
    order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
    # 鐵則 {已收款後明細/總額不可改}：生命週期的承重牆，砌在 update 入口。
    if not order.is_editable:
        raise HttpError(422, f'「{order.get_status_display()}」的訂單不可改明細（已收款後鎖定）')
    # 訂單一成立就把應收開給「當時的客戶」，分錄 append-only 不會改指向——所以不准換客戶。
    if payload.member_id != order.member_id:
        raise HttpError(422, '訂單成立後不可換客戶（帳已開給原客戶）；要換請作廢後重開一張')
    old_total = order.total          # 改單前總額（算帳款差額用）
    order.items.all().delete()
    _add_items(order, payload.items)
    order.recalc_total()
    order.post_adjustment(old_total)  # 帳款連動：總額變動補一筆調整（append-only 更正）
    return order


@router.delete('/{order_id}', response=MessageSchema)
def delete_order(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    # 訂單一成立就開了應收（帳款分錄），是財務單據——不可硬刪：刪了斷帳、且會 bulk 改寫 append-only 分錄。
    # 要取消請用「作廢」（狀態轉已取消並沖銷未收），帳務軌跡保留。
    if order.ledger_entries.exists():
        raise HttpError(422, '此訂單已開帳，不能刪除；請用「作廢」取消（保留帳務軌跡）')
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
# 整段包 atomic：收款/作廢會連動帳款分錄（多表寫入），要嘛全成、要嘛全退。
@transaction.atomic
def _transition(order_id, action):
    # select_for_update(of=self)：鎖住訂單這一列，序列化並發轉移——否則兩個 pay 請求可能都通過
    # 狀態檢查、各記一筆收款分錄（重複計）。of=('self',) 只鎖訂單、不鎖 join 進來的客戶。
    order = get_object_or_404(
        Order.objects.select_for_update(of=('self',)).select_related('member').prefetch_related('items'),
        pk=order_id,
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
