"""報價單的 API。規則來源：能力包/其他/報價單.md。刻意跟 order/apis.py 同形。

CRUD ＋ 關聯 ＋ 鐵則（把報價單建起來的部分）：
- 讀清單（帶條件、分頁）→ GET  /quotations
- 建立                  → POST /quotations
- 修改                  → PUT  /quotations/{id}
- 刪除                  → DELETE /quotations/{id}
（客戶從 apps/member、商品從 apps/product 各自的端點取——這裡不重複。）

狀態機轉移端點（主戲：每個動作對應一條合法轉移）：
- 送出 → POST /quotations/{id}/send   （草稿 → 已送出）
- 成交 → POST /quotations/{id}/win    （已送出 → 已成交，**生一張訂單**）
- 作廢 → POST /quotations/{id}/void   （草稿 / 已送出 → 已作廢）
非法轉移（終態不可轉、跳步不可轉）由 model 的 apply_transition 擋 → 422。

鐵則在門口與 model 兩層把關：
- {至少一筆明細}   → QuotationIn 的 min_length=1（schemas.py）
- {明細=目錄快照}  → QuotationItem.snapshot_from（models.py），本檔只給 product_id + qty
- {下架商品不可報價} → 本檔建報價時擋（is_active）
- {小計=數量×單價} → QuotationItem.save()（models.py）
- {總額=明細加總}  → 每次明細變動後 recalc_total()（本檔）
- {已送出後不可改} → update_quotation 先查 is_editable（本檔）
- {合法轉移}       → Quotation.apply_transition（models.py）
- {成交生訂單}     → win 走 apply_transition，本檔包 transaction.atomic（多表寫入）
"""
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from apps.member.models import Member
from apps.product.models import Product
from apps.quotation.models import Quotation, QuotationItem, TransitionError
from apps.quotation.schemas import (
    MessageSchema,
    QuotationIn,
    QuotationListSchema,
    QuotationNoteIn,
    QuotationSchema,
)

router = Router(tags=['quotation'])


def _add_items(quotation, items):
    """把 payload 的明細（product_id + quantity）建成報價明細——各自抄目錄快照。

    下架商品不可報價（{下架=停售}）→ 422。品名/單價由 snapshot_from 從目錄抄，
    前端傳的價格一律不採信。
    """
    for item in items:
        product = get_object_or_404(Product, pk=item.product_id)
        if not product.is_active:
            raise HttpError(422, f'商品「{product.name}」已下架，不能報價')
        QuotationItem.snapshot_from(quotation, product, item.quantity)


@transaction.atomic  # 報價＋明細要嘛全存、要嘛全不存——不留「有單無明細」的半成品
def make_quotation(customer, items, note=''):
    """把「一位客戶 + 一批明細」做成一張報價。建報價的鐵則（快照 / 小計 / 總額）全在這裡發火。"""
    quotation = Quotation.objects.create(customer=customer, note=note)
    _add_items(quotation, items)      # 各明細從目錄抄快照 + save() 算小計（鐵則）
    quotation.recalc_total()          # 鐵則：總額 = 明細加總
    return quotation


_QS = Quotation.objects.select_related('customer', 'order').prefetch_related('items')


# ── 報價單 CRUD ──────────────────────────────────────────────
@router.get('', response=QuotationListSchema)
def list_quotations(request, page: int = 1, page_size: int = 10, search: str = '', status: str = '', customer_id: int = None):
    """讀清單——**後端完整篩選**：status 篩狀態、search 模糊搜(客戶名/單號)、customer_id 精準、page/page_size 分頁。

    status_counts：各狀態的筆數（在 search 篩選後、status 篩選前算），給狀態頁籤的計數。
    """
    qs = _QS.order_by('-id')
    if search:
        qs = qs.filter(Q(customer__name__icontains=search) | Q(quote_no__icontains=search))
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    # .order_by() 清掉預設排序，否則會混進 GROUP BY 讓聚合拆成一筆一組
    by_status = {r['status']: r['n'] for r in qs.order_by().values('status').annotate(n=Count('id'))}
    status_counts = {'all': sum(by_status.values()),
                     **{s: by_status.get(s, 0) for s, _ in Quotation.Status.choices}}
    if status and status != 'all':
        qs = qs.filter(status=status)
    count = qs.count()
    start = (max(page, 1) - 1) * page_size
    return {'items': list(qs[start:start + page_size]), 'count': count, 'status_counts': status_counts}


@router.get('/{quotation_id}', response=QuotationSchema)
def get_quotation(request, quotation_id: int):
    return get_object_or_404(_QS, pk=quotation_id)


@router.post('', response=QuotationSchema)
def create_quotation(request, payload: QuotationIn):
    """後台建報價：客戶由前端指定（customer_id）——業務替客人建報價。"""
    customer = get_object_or_404(Member, pk=payload.customer_id)
    return make_quotation(customer, payload.items, payload.note)


@router.put('/{quotation_id}', response=QuotationSchema)
@transaction.atomic
def update_quotation(request, quotation_id: int, payload: QuotationIn):
    """改報價（客戶與明細整組替換——最好懂的更新語意）。"""
    quotation = get_object_or_404(Quotation, pk=quotation_id)
    # 鐵則 {已送出後明細/總額不可改}：生命週期的承重牆，砌在 update 入口。
    if not quotation.is_editable:
        raise HttpError(422, f'「{quotation.get_status_display()}」的報價不可改明細（送出後鎖定）')
    quotation.customer = get_object_or_404(Member, pk=payload.customer_id)
    quotation.note = payload.note
    quotation.save(update_fields=['customer', 'note', 'updated_at'])
    quotation.items.all().delete()
    _add_items(quotation, payload.items)
    quotation.recalc_total()
    return quotation


@router.delete('/{quotation_id}', response=MessageSchema)
def delete_quotation(request, quotation_id: int):
    quotation = get_object_or_404(Quotation, pk=quotation_id)
    quote_no = quotation.quote_no
    quotation.delete()  # 明細跟著刪（models 的 on_delete=CASCADE）
    return {'message': f'報價單 {quote_no} 已刪除'}


@router.post('/{quotation_id}/note', response=QuotationSchema)
def update_quotation_note(request, quotation_id: int, payload: QuotationNoteIn):
    """只改備註（自由文字，跟狀態無關；前端備註欄 inline dialog 用）。"""
    quotation = get_object_or_404(_QS, pk=quotation_id)
    quotation.note = payload.note
    quotation.save(update_fields=['note', 'updated_at'])
    return quotation


# ── 報價單狀態機：一個動作一個端點，都走 model 的 apply_transition ──
# 非法轉移由 model 擋（TransitionError）→ 這裡統一轉成 422 給前端顯示白話原因。
# 整段包 atomic：win 會生訂單（多表寫入），要嘛全成、要嘛全退。
@transaction.atomic
def _transition(quotation_id, action):
    quotation = get_object_or_404(_QS, pk=quotation_id)
    try:
        quotation.apply_transition(action)
    except TransitionError as e:
        raise HttpError(422, str(e))
    except ValueError as e:          # assert_total_consistent：金額守恆破了
        raise HttpError(422, str(e))
    return quotation


@router.post('/{quotation_id}/send', response=QuotationSchema)
def send_quotation(request, quotation_id: int):
    """送出：草稿 → 已送出（送出後明細鎖定）。"""
    return _transition(quotation_id, 'send')


@router.post('/{quotation_id}/win', response=QuotationSchema)
def win_quotation(request, quotation_id: int):
    """成交：已送出 → 已成交（終態；**生一張訂單**，用報價的凍結價成交）。"""
    return _transition(quotation_id, 'win')


@router.post('/{quotation_id}/void', response=QuotationSchema)
def void_quotation(request, quotation_id: int):
    """作廢：草稿 / 已送出 → 已作廢（終態；沒談成/取消報價）。"""
    return _transition(quotation_id, 'void')
