"""Background scan tasks."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models import Scan, Target
from app.services.orchestrator import ScanOrchestrator

logger = logging.getLogger("apishield.tasks.scans")


async def _mark_failed(session: AsyncSession, scan_id: int, reason: str) -> None:
    """Record a terminal failure so the scan never stays "running" forever."""
    scan = await session.get(Scan, scan_id)
    if scan is None:
        return
    scan.status = "failed"
    scan.finished_at = datetime.now(timezone.utc)
    await session.commit()


@celery_app.task(name="scans.run_scan")
def run_scan(scan_id: int, target_id: int) -> dict:
    """Run a queued scan in the background.

    The scan API creates the Scan row (status ``queued``) and passes its id
    here, so every scan has a real, client-visible id from the moment it is
    requested and can be marked ``failed`` when the worker cannot finish it.
    """

    async def _run() -> dict:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target = await session.get(Target, target_id)
                if target is None:
                    await _mark_failed(session, scan_id, "target not found")
                    return {"status": "error", "reason": "target not found"}
                try:
                    result = await ScanOrchestrator().run_scan(
                        target, session, scan_id=scan_id
                    )
                except Exception as exc:
                    # A systemic failure (database, unexpected bug) must leave
                    # the scan in a terminal state, not "running" forever.
                    logger.exception("Scan %s failed", scan_id)
                    await session.rollback()
                    await _mark_failed(session, scan_id, str(exc))
                    return {
                        "status": "failed",
                        "scan_db_id": scan_id,
                        "reason": str(exc),
                    }
                return {
                    "status": "completed",
                    "target_id": target_id,
                    "scan_db_id": result.scan_id,
                    "findings": len(result.findings),
                    "errors": result.errors,
                }
        finally:
            await engine.dispose()

    return asyncio.run(_run())
