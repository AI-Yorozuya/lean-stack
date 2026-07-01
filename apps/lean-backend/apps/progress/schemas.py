"""progress app 的 ninja schema。"""
from ninja import Schema


class JobSchema(Schema):
    id: int
    name: str
    status: str
    progress: int
    message: str
