import threading
import time
import logging
from datetime import datetime
from pathlib import Path

from bot_insta.src.core.scheduler_manager import scheduler_manager
from bot_insta.src.core.video_engine import create_reel
from bot_insta.src.core.uploader_factory import UploaderFactory
from bot_insta.src.core.history_manager import history_manager
from bot_insta.src.core.config_loader import config
from bot_insta.src.core.account_manager import acc_manager
from bot_insta.src.gui.utils import make_video_context
from bot_insta.src.gui.bootstrap import PROJECT_ROOT

log = logging.getLogger(__name__)

class SchedulerWorker:
    def __init__(self):
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            log.info("Scheduler thread started.")

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
            
    def _run_loop(self):
        while not self.stop_event.is_set():
            try:
                self._process_pending_jobs()
            except Exception as e:
                log.error("Error in scheduler loop: %s", e)
            
            # Sleep in short bursts to allow quick teardown
            for _ in range(30):
                if self.stop_event.is_set():
                    break
                time.sleep(1.0)
                
    def _process_pending_jobs(self):
        jobs = scheduler_manager.get_pending_jobs()
        for job in jobs:
            if self.stop_event.is_set():
                break
                
            job_id = job["id"]
            log.info(f"Scheduler processing job {job_id}...")
            scheduler_manager.update_job_status(job_id, "processing")
            
            try:
                file_path = job.get("file_path")
                if job.get("type") == "render_and_upload":
                    # We need to generate the reel first
                    profile = job.get("profile", "default")
                    q_over = job.get("quotes_override")
                    q_over = config.get_quote_file(q_over) if q_over else None
                    ctx = make_video_context(config, profile, quotes_file_override=q_over)
                    reel_path = create_reel(ctx)
                    file_path = str(reel_path)
                    scheduler_manager.update_job_file(job_id, file_path)
                    history_manager.log_event(Path(file_path).name, job.get("platform", "Local"), job.get("account_id", "local"), "Generated (JIT)")

                target_platform = job.get("platform", "Local")
                acc_id = job.get("account_id")
                caption = job.get("caption", "")

                if target_platform != "Local":
                    creds = acc_manager.get_account(acc_id).get("credentials", {})
                    proxy = acc_manager.get_account(acc_id).get("proxy")
                    
                    if target_platform == "Instagram" and acc_id:
                        creds["session_override"] = str(PROJECT_ROOT / "bot_insta" / "config" / f"session_{acc_id}.json")
                        
                    uploader = UploaderFactory.get_uploader(target_platform)
                    abort_evt = threading.Event()
                    
                    mid = uploader.upload(Path(file_path), caption=caption, credentials=creds, proxy=proxy, abort_event=abort_evt)
                    log.info(f"Scheduler job finished uploading: {mid}")
                    history_manager.log_event(Path(file_path).name, target_platform, acc_id, "Success (Scheduled)", mid)
                    acc_manager.update_status(acc_id, "Active")
                else:
                    if file_path:
                        history_manager.log_event(Path(file_path).name, "Local", "local", "Generated (Scheduled)")
                
                # Success, remove from queue
                scheduler_manager.delete_job(job_id)
                
            except Exception as e:
                log.error("Job %s failed: %s", job_id, e)
                import traceback
                traceback.print_exc()
                scheduler_manager.update_job_status(job_id, "failed", str(e))
                if job.get("account_id"):
                    acc_manager.update_status(job.get("account_id"), "Error")

scheduler_worker = SchedulerWorker()
