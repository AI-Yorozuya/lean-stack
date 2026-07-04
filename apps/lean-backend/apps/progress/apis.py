"""progress app 的 API（ninja Router）。

端點：
- GET  /progress    → 列出所有背景任務（背景任務頁的清單，最新在前）。
- POST /progress/demo → 建一個 Job(PENDING)，派工給 worker，回 job 資料（含 id）。
- GET  /progress/{id} → 查這個 Job 現在的 status / progress / message（前端輪詢用）。

派工關鍵：`run_demo_job.delay(job.id)` 把任務丟進 redis 佇列「立刻回傳」，
不會卡住 HTTP request —— 實際執行由背景的 celery worker 處理。
"""
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.progress.models import Job
from apps.progress.schemas import JobSchema
from apps.progress.tasks import run_demo_job

router = Router(tags=['progress'])


@router.get('', response=list[JobSchema])
def list_jobs(request):
    """列出所有背景任務（最新在前）。前端只要有 RUNNING 就每 3 秒輪詢這支。"""
    return Job.objects.order_by('-id')


@router.post('/demo', response=JobSchema)
def start_demo_job(request):
    """建一個示範任務並派工。"""
    job = Job.objects.create(name='示範任務')   # 預設 PENDING
    run_demo_job.delay(job.id)                   # 丟進佇列，馬上回
    return job


@router.get('/{job_id}', response=JobSchema)
def get_job(request, job_id: int):
    """查任務進度（前端每秒輪詢這支）。"""
    return get_object_or_404(Job, pk=job_id)
