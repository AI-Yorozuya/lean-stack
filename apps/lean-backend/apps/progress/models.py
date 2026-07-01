"""非同步任務的進度，存在 DB。

教學重點：worker 在背景跑、前端用 HTTP 輪詢看進度 —— 兩邊不直接溝通，
而是「都讀寫同一張 Job 表」。這是最白話、最好教的 async 進度做法
（不用 websocket、不用 celery result 細節，一張表就懂）。
"""
from django.db import models

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

    def __str__(self):
        return f'Job#{self.pk} {self.name} [{self.status}] {self.progress}%'

    # ── 狀態轉換 helper：集中在 model，task 只管呼叫 ──────────────
    def mark_running(self):
        self.status = self.Status.RUNNING
        self.progress = 0
        self.save(update_fields=['status', 'progress', 'updated_at'])

    def set_progress(self, percent, message=''):
        self.progress = max(0, min(100, int(percent)))  # 夾在 0–100
        if message:
            self.message = message
        self.save(update_fields=['progress', 'message', 'updated_at'])

    def mark_success(self, message='完成'):
        self.status = self.Status.SUCCESS
        self.progress = 100
        self.message = message
        self.save(update_fields=['status', 'progress', 'message', 'updated_at'])

    def mark_failed(self, message):
        self.status = self.Status.FAILED
        self.message = str(message)
        self.save(update_fields=['status', 'message', 'updated_at'])
