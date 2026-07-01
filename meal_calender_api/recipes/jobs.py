"""In-process background job runner for recipe generation."""

from __future__ import annotations

import logging
import threading

from django.db import close_old_connections
from django.utils import timezone

from .models import RecipeGenerationJob
from .services import generate_and_store_weekly_recipes

logger = logging.getLogger(__name__)


def _run_recipe_generation_job(job_id: int) -> None:
    """Execute one queued recipe generation job in a background thread."""
    close_old_connections()
    try:
        job = RecipeGenerationJob.objects.get(id=job_id)
    except RecipeGenerationJob.DoesNotExist:
        logger.warning("Recipe generation job %s no longer exists", job_id)
        close_old_connections()
        return

    job.status = RecipeGenerationJob.Status.RUNNING
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_message"])

    try:
        generate_and_store_weekly_recipes(job)
        job.status = RecipeGenerationJob.Status.SUCCEEDED
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])
    except Exception as exc:
        logger.exception("Recipe generation job failed", extra={"job_id": job_id})
        job.status = RecipeGenerationJob.Status.FAILED
        job.completed_at = timezone.now()
        job.error_message = str(exc)
        job.save(update_fields=["status", "completed_at", "error_message"])
    finally:
        close_old_connections()


def enqueue_recipe_generation_job(job_id: int) -> None:
    """Queue recipe generation to run outside the request thread."""
    worker = threading.Thread(
        target=_run_recipe_generation_job,
        args=(job_id,),
        daemon=True,
    )
    worker.start()
