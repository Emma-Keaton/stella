"""
src/backend/starnet/cron_scheduler.py — Cron / autonomous scheduler (StarNet cron-driver.js port).

Jobs are opt-in. Each job has a cron expression, prompt, agent id, and enabled
flag. runTick() checks due jobs and returns those that should fire.
The timer/clock lives in the composition root so this stays testable.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional


@dataclass
class CronJob:
    id: str
    cron_expr: str
    prompt: str
    agent_id: str = "default"
    enabled: bool = True
    next_fire: Optional[float] = None
    last_run: Optional[float] = None


class CronScheduler:
    """In-memory cron job scheduler with tick-based due-job detection."""

    def __init__(self) -> None:
        self._jobs: dict[str, CronJob] = {}
        self._lock = threading.RLock()

    def add_job(self, job: CronJob) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def get_job(self, job_id: str) -> Optional[CronJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def all_jobs(self) -> list[CronJob]:
        with self._lock:
            return list(self._jobs.values())

    def enable(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.enabled = True

    def disable(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.enabled = False

    def run_tick(self, now: Optional[float] = None) -> list[CronJob]:
        """Return jobs that are enabled and due to fire at `now` (epoch seconds)."""
        if now is None:
            import time
            now = time.time()
        with self._lock:
            due: list[CronJob] = []
            for job in self._jobs.values():
                if job.enabled and (job.next_fire is None or job.next_fire <= now):
                    due.append(job)
            return due

    def schedule_next_fire(self, job_id: str, next_fire_seconds: float) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.next_fire = next_fire_seconds

    def mark_run(self, job_id: str, last_run_seconds: float) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.last_run = last_run_seconds

    def shutdown(self) -> None:
        pass