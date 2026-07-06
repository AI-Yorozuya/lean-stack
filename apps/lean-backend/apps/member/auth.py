"""會員登入的憑證（token）與守衛。規則來源：intents/會員登入.md。

**教學版刻意用 Django 內建的 `django.core.signing`，不用 JWT。**
- 生產級做法見 top-erp（PyJWT，access + refresh、audience…）；那是「築起高牆」的下游。
- 這裡只要證明同一套概念：**登入成功 → 發一張有簽章、會過期的憑證 → 之後請求把它帶在
  `Authorization: Bearer <token>` → 守衛驗章 + 查人**。少一個依賴（pyproject 本就刻意砍掉 pyjwt）。

token 內容只放 `member_id`，用 SECRET_KEY 簽章（改不了、偽造不了），逾期自動失效。
"""
from django.core import signing
from ninja.errors import HttpError
from ninja.security import HttpBearer

from apps.member.models import Member

_SALT = 'member-login'                 # 簽章命名空間（跟別處的 signing 不會互相解到）
TOKEN_MAX_AGE = 7 * 24 * 60 * 60       # 憑證有效期：7 天


def issue_token(member: Member) -> str:
    """登入成功時發憑證：把 member_id 簽起來。"""
    return signing.dumps({'member_id': member.id}, salt=_SALT)


class MemberAuth(HttpBearer):
    """會員憑證守衛。掛在要「登入才能用」的端點上：

        @router.get('/me', auth=member_auth)
        def me(request):
            return request.auth   # ← 驗過的 Member 物件

    驗不過一律 401（章不對／過期／查無此人或已停用）。
    """

    def authenticate(self, request, token):
        try:
            data = signing.loads(token, salt=_SALT, max_age=TOKEN_MAX_AGE)
        except signing.SignatureExpired:
            raise HttpError(401, '登入已過期，請重新登入')
        except signing.BadSignature:
            raise HttpError(401, '登入憑證無效，請重新登入')

        member = Member.objects.filter(
            id=data.get('member_id'), status=Member.Status.ACTIVE
        ).first()
        if not member:
            raise HttpError(401, '會員不存在或已停用')
        return member


member_auth = MemberAuth()
