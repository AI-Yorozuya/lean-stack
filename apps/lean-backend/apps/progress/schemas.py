"""progress app 的 ninja schema。"""
from typing import Optional

from ninja import Schema


class JobSchema(Schema):
    id: int
    name: str
    status: str                              # code（PENDING / RUNNING / …）
    status_display: str                      # 中文（排隊中 / 執行中 / …）
    progress: int
    message: str
    started_at: Optional[str] = None         # 開始執行（ISO 字串）
    completed_at: Optional[str] = None       # 結束
    elapsed_seconds: Optional[float] = None  # 花費秒數

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_started_at(obj):
        return obj.started_at.isoformat() if obj.started_at else None

    @staticmethod
    def resolve_completed_at(obj):
        return obj.completed_at.isoformat() if obj.completed_at else None
