"""非同步任務的進度，存在 DB。

教學重點：worker 在背景跑、前端用 HTTP 輪詢看進度 —— 兩邊不直接溝通，
而是「都讀寫同一張 Job 表」。這是最白話、最好教的 async 進度做法
（不用 websocket、不用 celery result 細節，一張表就懂）。
"""
from django.db import models
from django.utils import timezone

from apps._common.models import TimeStampedModel


class Job(TimeStampedModel):
    """一次背景任務的執行紀錄。"""

    class Status(models.TextChoices):
        PENDING = 'PENDING', '排隊中'
        RUNNING = 'RUNNING', '執行中'
        SUCCESS = 'SUCCESS', '完成'
        FAILED = 'FAILED', '失敗'

    name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    progress = models.IntegerField(default=0)  # 0–100
    message = models.TextField(blank=True)      # 給人看的訊息（失敗原因等）
    started_at = models.DateTimeField(null=True, blank=True)    # 開始執行（mark_running 時記）
    completed_at = models.DateTimeField(null=True, blank=True)  # 結束（成功/失敗時記）

    def __str__(self):
        return f'Job#{self.pk} {self.name} [{self.status}] {self.progress}%'

    @property
    def elapsed_seconds(self):
        """花費秒數（開始→結束）。還沒結束就回 None。"""
        if self.started_at and self.completed_at:
            return round((self.completed_at - self.started_at).total_seconds(), 2)
        return None

    # ── 狀態轉換 helper：集中在 model，task 只管呼叫 ──────────────
    def mark_running(self):
        self.status = self.Status.RUNNING
        self.progress = 0
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'progress', 'started_at', 'updated_at'])

    def set_progress(self, percent, message=''):
        self.progress = max(0, min(100, int(percent)))  # 夾在 0–100
        if message:
            self.message = message
        self.save(update_fields=['progress', 'message', 'updated_at'])

    def mark_success(self, message='完成'):
        self.status = self.Status.SUCCESS
        self.progress = 100
        self.message = message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'progress', 'message', 'completed_at', 'updated_at'])

    def mark_failed(self, message):
        self.status = self.Status.FAILED
        self.message = str(message)
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'message', 'completed_at', 'updated_at'])
