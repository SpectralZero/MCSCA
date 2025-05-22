from __future__ import annotations
import customtkinter as ctk

class JobTracker(ctk.CTkFrame):
    def __init__(self, *args, **kwargs):
        # note: assumes your CTkFrame subclasses call super().__init__
        super().__init__(*args, **kwargs)
        self._jobs: set[str] = set()

    def schedule(self, ms: int, callback: callable) -> str:
        """Schedule and track an after-job."""
        job = self.after(ms, callback)
        self._jobs.add(job)
        return job

    def cancel_all_jobs(self):
        """Cancel everything we scheduled."""
        for job in list(self._jobs):
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._jobs.clear()

    def destroy(self):
        # make sure jobs go away before widget is torn down
        self.cancel_all_jobs()
        super().destroy()
