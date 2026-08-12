"""Celery application: Redis broker/backend for background scan workers."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "apishield",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.scans"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    enable_utc=True,
    timezone="UTC",
)
