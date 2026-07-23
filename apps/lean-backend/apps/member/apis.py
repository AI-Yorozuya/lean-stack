"""客戶管理 API。規則來源：intents/會員管理.md。

- 登入             → POST /member/login   （發憑證）
- 我是誰（受保護） → GET  /member/me      （帶憑證才進得來）
- 列表（搜尋 + 分頁）→ GET  /member
- 建立             → POST /member
- 改（姓名/電話）  → PUT  /member/{id}
- 停用             → POST /member/{id}/deactivate
- 重新啟用         → POST /member/{id}/reactivate

鐵則把關：
- {一 email 一客戶} → email unique（DB），撞了轉 422 白話。
- {停用=關閉不刪}   → 只有 deactivate 改狀態，**沒有 DELETE 端點**。
- {登入才是本人}   → /login 驗雜湊密碼發憑證；/me 靠 member_auth 守衛（見 auth.py）。
"""
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from apps.member.auth import issue_token, member_auth
from apps.member.models import Member
from apps.member.schemas import (
    LoginIn,
    LoginOut,
    MemberIn,
    MemberListSchema,
    MemberSchema,
    MemberUpdateIn,
)

router = Router(tags=['member'])


# ── 登入 / 我是誰 ──────────────────────────
@router.post('/login', response=LoginOut)
def login(request, payload: LoginIn):
    """帳號密碼登入：對到客戶 + 密碼正確 → 發一張憑證。

    帳號或密碼錯都回同一句 401（不透露是哪個錯，別幫人試帳號）。
    真驗密碼在這裡發生（雜湊比對）——那張「示範密碼」到此變成後端認證。
    """
    member = Member.objects.filter(
        email=payload.email.strip().lower(), status=Member.Status.ACTIVE
    ).first()
    if not member or not member.check_password(payload.password):
        raise HttpError(401, '帳號或密碼錯誤')
    return {'access_token': issue_token(member), 'member': member}


@router.get('/me', response=MemberSchema, auth=member_auth)
def me(request):
    """回「我是誰」——只有帶著有效憑證才進得來（守衛驗過的 Member）。

    這支就是「憑證真的鎖得住東西」的證明：沒 token / token 壞 / 過期 → 401。
    """
    return request.auth


@router.get('', response=MemberListSchema)
def list_members(request, page: int = 1, page_size: int = 10, search: str = '', status: str = ''):
    """search 模糊搜姓名，status 精準篩（ACTIVE/INACTIVE），page/page_size 分頁。"""
    qs = Member.objects.order_by('name')
    if search:
        qs = qs.filter(name__icontains=search)
    if status:
        qs = qs.filter(status=status)
    count = qs.count()
    start = (max(page, 1) - 1) * page_size
    return {'items': list(qs[start:start + page_size]), 'count': count}


@router.post('', response=MemberSchema)
def create_member(request, payload: MemberIn):
    try:
        return Member.objects.create(**payload.dict())
    except IntegrityError:
        # {一 email 一客戶}：DB unique 擋下，轉成前端看得懂的話。
        raise HttpError(422, f'email「{payload.email}」已被使用（一 email 一客戶）')


@router.put('/{member_id}', response=MemberSchema)
def update_member(request, member_id: int, payload: MemberUpdateIn):
    """改姓名/電話（email 不給改——見 schemas 的說明）。"""
    member = get_object_or_404(Member, pk=member_id)
    member.name = payload.name
    member.phone = payload.phone
    member.save(update_fields=['name', 'phone', 'updated_at'])
    return member


@router.post('/{member_id}/deactivate', response=MemberSchema)
def deactivate_member(request, member_id: int):
    """停用：把狀態關成 INACTIVE，資料保留（不 DELETE）。"""
    member = get_object_or_404(Member, pk=member_id)
    member.status = Member.Status.INACTIVE
    member.save(update_fields=['status', 'updated_at'])
    return member


@router.post('/{member_id}/reactivate', response=MemberSchema)
def reactivate_member(request, member_id: int):
    """重新啟用：復用舊客戶。"""
    member = get_object_or_404(Member, pk=member_id)
    member.status = Member.Status.ACTIVE
    member.save(update_fields=['status', 'updated_at'])
    return member
