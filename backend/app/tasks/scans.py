"""Background scan tasks."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models import Target
from app.services.orchestrator import ScanOrchestrator


@celery_app.task(name="scans.run_scan")
def run_scan(target_id: int) -> dict:
    """Run a scan for a target in the background."""

    async def _run() -> dict:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target = await session.get(Target, target_id)
                if target is None:
                    return {"status": "error", "reason": "target not found"}
                result = await ScanOrchestrator().run_scan(target, session)
                return {
                    "status": "completed",
                    "target_id": target_id,
                    "findings": len(result.findings),
                }
        finally:
            await engine.dispose()

    return asyncio.run(_run())
