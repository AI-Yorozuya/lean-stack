"""帳款的 API。規則來源：能力包/主幹/收費.md。

帳款頁是**唯讀投影**：分錄由訂單生命週期產生（建單→應收、收款→收款、作廢→沖銷），
這裡只把 append-only 的分錄「算成」餘額與明細給人看。沒有「改餘額」的端點——
要動帳只能在訂單那邊做動作，再由 model append 分錄（真相一處、可稽核）。

- 客戶應收總覽（一列一客戶，欠最多的在前）→ GET /billing/receivables
- 單一客戶的分錄流（含跑動餘額）              → GET /billing/customers/{id}/ledger
"""
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.billing.models import LedgerEntry
from apps.billing.schemas import CustomerLedgerSchema, ReceivableListSchema
from apps.member.models import Member

router = Router(tags=['billing'])

_Z = Decimal('0')


@router.get('/receivables', response=ReceivableListSchema)
def list_receivables(request, only_outstanding: bool = False):
    """客戶應收總覽：每個有帳的客戶一列（應收/已收/餘額），欠最多的排前面。

    only_outstanding=True 時只回還有欠款（餘額 > 0）的客戶。
    """
    # 一次 group by 客戶把三種分錄聚合起來（後端算完只回結果，不把整條分錄流丟前端）。
    rows = (
        LedgerEntry.objects
        .values('customer', 'customer__name', 'customer__phone')
        .annotate(
            charged=Sum('amount', filter=Q(kind=LedgerEntry.Kind.CHARGE)),
            paid=Sum('amount', filter=Q(kind=LedgerEntry.Kind.PAYMENT)),
            reversed_=Sum('amount', filter=Q(kind=LedgerEntry.Kind.REVERSAL)),
            entry_count=Count('id'),
        )
    )
    items = []
    total_balance = _Z
    for r in rows:
        charged = r['charged'] or _Z
        paid = r['paid'] or _Z
        balance = charged - paid - (r['reversed_'] or _Z)
        if only_outstanding and balance <= 0:
            continue
        total_balance += balance
        items.append({
            'customer': {'id': r['customer'], 'name': r['customer__name'], 'phone': r['customer__phone']},
            'charged': charged,
            'paid': paid,
            'balance': balance,
            'entry_count': r['entry_count'],
        })
    items.sort(key=lambda x: x['balance'], reverse=True)  # 欠最多的在前
    return {'items': items, 'count': len(items), 'total_balance': total_balance}


@router.get('/customers/{customer_id}/ledger', response=CustomerLedgerSchema)
def customer_ledger(request, customer_id: int):
    """單一客戶的分錄流：依時間序逐筆列出，後端算好「跑動餘額」給人對帳。"""
    customer = get_object_or_404(Member, pk=customer_id)
    entries = list(
        LedgerEntry.objects.filter(customer=customer).select_related('order').order_by('id')
    )
    running = _Z
    charged = paid = _Z
    out = []
    for e in entries:
        running += e.signed_amount           # 逐筆累加＝跑動餘額（分錄流是時間序）
        if e.kind == LedgerEntry.Kind.CHARGE:
            charged += e.amount
        elif e.kind == LedgerEntry.Kind.PAYMENT:
            paid += e.amount
        out.append({
            'id': e.id,
            'date': str(e.created_at.date()),
            'kind': e.kind,
            'kind_display': e.get_kind_display(),
            'amount': e.amount,
            'signed_amount': e.signed_amount,
            'order_no': e.order.order_no if e.order else None,
            'order_id': e.order_id,
            'memo': e.memo,
            'running_balance': running,
        })
    return {
        'customer': {'id': customer.id, 'name': customer.name, 'phone': customer.phone},
        'charged': charged,
        'paid': paid,
        'balance': LedgerEntry.balance_for(customer),
        'entries': out,
    }
