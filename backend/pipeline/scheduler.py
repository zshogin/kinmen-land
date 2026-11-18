from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, Dict, Any
from .etl_pipeline import etl_pipeline

class PipelineScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def start(self):
        """Start the background decennial scheduler (1st, 11th, 21st at 04:00 AM)"""
        if self.is_running:
            return

        # Trigger on 1st, 11th, and 21st of every month at 04:00 AM
        trigger = CronTrigger(day="1,11,21", hour=4, minute=0)
        self.scheduler.add_job(
            func=self._cron_job_sync,
            trigger=trigger,
            id="moi_decennial_sync_job",
            name="內政部實價登錄每旬自動同步任務",
            replace_existing=True
        )
        self.scheduler.start()
        self.is_running = True
        print(">> [Scheduler] Decennial ETL Scheduler started successfully (Cron: 1,11,21 04:00 AM)")

    def stop(self):
        """Stop scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            print(">> [Scheduler] Decennial ETL Scheduler stopped.")

    def trigger_manual_sync(self, batch_name: Optional[str] = None) -> Dict[str, Any]:
        """Manually trigger sync pipeline on demand"""
        return etl_pipeline.run_sync(batch_name=batch_name)

    def _cron_job_sync(self):
        print(">> [Scheduler Trigger] Running scheduled decennial MOI synchronization...")
        try:
            res = etl_pipeline.run_sync()
            print(f">> [Scheduler Trigger] Decennial sync completed: {res}")
        except Exception as e:
            print(f">> [Scheduler Trigger ERROR] Scheduled sync failed: {e}")

pipeline_scheduler = PipelineScheduler()
