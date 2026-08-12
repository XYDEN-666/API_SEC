"""Dashboard aggregation: owner-scoped summary stats (Task 13.1).

Every count is scoped through ``Project.owner_id``: the queries join
Project -> Target -> Scan -> Finding, so data belonging to other users can
never leak into a summary.
"""

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Finding, Project, Scan, Target

# Findings are grouped by their stored severity; "info" is included alongside
# the Low/Medium/High/Critical buckets so no findings are hidden.
SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
_SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITY_ORDER)}
_RANK_CASE = case(_SEVERITY_RANK, value=Finding.severity)


async def get_dashboard_summary(session: AsyncSession, user_id: int) -> dict:
    """Return aggregate stats for one user's own projects."""
    projects = (
        await session.scalar(
            select(func.count(Project.id)).where(Project.owner_id == user_id)
        )
    ) or 0
    targets = (
        await session.scalar(
            select(func.count(Target.id))
            .join(Project, Project.id == Target.project_id)
            .where(Project.owner_id == user_id)
        )
    ) or 0
    scans = (
        await session.scalar(
            select(func.count(Scan.id))
            .join(Target, Target.id == Scan.target_id)
            .join(Project, Project.id == Target.project_id)
            .where(Project.owner_id == user_id)
        )
    ) or 0

    severity_rows = (
        await session.execute(
            select(Finding.severity, func.count(Finding.id))
            .join(Scan, Scan.id == Finding.scan_id)
            .join(Target, Target.id == Scan.target_id)
            .join(Project, Project.id == Target.project_id)
            .where(Project.owner_id == user_id)
            .group_by(Finding.severity)
        )
    ).all()
    findings_by_severity = {severity: 0 for severity in SEVERITY_ORDER}
    for severity, count in severity_rows:
        findings_by_severity[severity] = count

    category_rows = (
        await session.execute(
            select(Finding.owasp_category, func.count(Finding.id))
            .join(Scan, Scan.id == Finding.scan_id)
            .join(Target, Target.id == Scan.target_id)
            .join(Project, Project.id == Target.project_id)
            .where(Project.owner_id == user_id)
            .group_by(Finding.owasp_category)
        )
    ).all()
    findings_by_category = {
        category: count for category, count in category_rows
    }

    recent_scan_rows = (
        await session.execute(
            select(Scan, Target.name)
            .join(Target, Target.id == Scan.target_id)
            .join(Project, Project.id == Target.project_id)
            .where(Project.owner_id == user_id)
            .order_by(Scan.id.desc())
            .limit(5)
        )
    ).all()

    recent_scans = []
    for scan, target_name in recent_scan_rows:
        top = (
            await session.execute(
                select(Finding.title, Finding.severity)
                .where(Finding.scan_id == scan.id)
                .order_by(_RANK_CASE.asc(), Finding.id.asc())
                .limit(1)
            )
        ).first()
        recent_scans.append(
            {
                "id": scan.id,
                "target_name": target_name,
                "status": scan.status,
                "started_at": scan.started_at,
                "finished_at": scan.finished_at,
                "top_finding": (
                    {"title": top.title, "severity": top.severity}
                    if top is not None
                    else None
                ),
            }
        )

    return {
        "total_projects": projects,
        "total_targets": targets,
        "total_scans": scans,
        "total_findings": sum(findings_by_severity.values()),
        "findings_by_severity": findings_by_severity,
        "findings_by_category": findings_by_category,
        "recent_scans": recent_scans,
    }
