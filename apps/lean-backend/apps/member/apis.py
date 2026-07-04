"""會員管理 API。規則來源：intents/會員管理.md。

- 列表（搜尋 + 分頁）→ GET  /member
- 建立             → POST /member
- 改（姓名/電話）  → PUT  /member/{id}
- 停用             → POST /member/{id}/deactivate
- 重新啟用         → POST /member/{id}/reactivate

鐵則把關：
- {一 email 一會員} → email unique（DB），撞了轉 422 白話。
- {停用=關閉不刪}   → 只有 deactivate 改狀態，**沒有 DELETE 端點**。
"""
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from apps.member.models import Member
from apps.member.schemas import (
    MemberIn,
    MemberListSchema,
    MemberSchema,
    MemberUpdateIn,
)

router = Router(tags=['member'])


@router.get('', response=MemberListSchema)
def list_members(request, page: int = 1, page_size: int = 10, q: str = '', status: str = ''):
    """q 模糊搜姓名，status 精準篩（ACTIVE/INACTIVE），page/page_size 分頁。"""
    qs = Member.objects.order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)
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
        # {一 email 一會員}：DB unique 擋下，轉成前端看得懂的話。
        raise HttpError(422, f'email「{payload.email}」已被使用（一 email 一會員）')


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
    """重新啟用：復用舊會員。"""
    member = get_object_or_404(Member, pk=member_id)
    member.status = Member.Status.ACTIVE
    member.save(update_fields=['status', 'updated_at'])
    return member
