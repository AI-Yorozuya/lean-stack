"""會員的輸入/輸出形狀（ninja Schema）。

教學重點：
- 「In」＝進來的（建立/修改）；其他＝出去的（回前端）。
- email 只在「建立」時給——{一 email 一會員}，改資料時不讓動 email（改 email 等於換人）。
"""
from ninja import Field, Schema


class MemberIn(Schema):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1)
    phone: str = ''


class MemberUpdateIn(Schema):
    # 刻意沒有 email：鐵則上 email 是會員的識別，建立後不給改。
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = ''


class MemberSchema(Schema):
    id: int
    name: str
    email: str
    phone: str
    registered_at: str       # 註冊日期（= created_at 的日期，TimeStampedModel 自動記）
    status: str              # 狀態 code（ACTIVE / INACTIVE）
    status_display: str      # 中文（啟用 / 停用）

    @staticmethod
    def resolve_registered_at(obj):
        return str(obj.created_at.date())

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()


class MemberListSchema(Schema):
    """列表回應：items + count，配前端 table + pagination。"""
    items: list[MemberSchema]
    count: int


class MessageSchema(Schema):
    message: str
