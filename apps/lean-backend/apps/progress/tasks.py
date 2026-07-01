"""Celery 任務。autodiscover 會自動掃到這個檔。

這裡只有一個「明顯是教學示範」的長任務：什麼都不做，只是慢慢把進度從 0 推到 100，
證明「前端按按鈕 → 後端派工 → worker 背景跑 → 前端輪詢看進度」整條 async 路通了。
"""
import time

from celery import shared_task

from apps.progress.models import Job


@shared_task
def run_demo_job(job_id):
    """示範用長任務：0 → 100，每步小睡一下。

    用 @shared_task（不綁特定 Celery 實例）是 app 內任務的慣例。
    真實任務會把「實際工作」放進這個迴圈裡（匯出報表、跑批次…）。
    """
    job = Job.objects.get(pk=job_id)
    try:
        job.mark_running()
        for percent in range(0, 101, 10):       # 0,10,...,100 共 11 步
            time.sleep(0.5)                      # 假裝在做很慢的事
            job.set_progress(percent, message=f'處理中… {percent}%')
        job.mark_success('示範任務完成')
    except Exception as exc:                     # 任何錯都記成 FAILED，前端看得到原因
        job.mark_failed(exc)
        raise                                    # 仍往上拋，讓 worker log 有完整 traceback
