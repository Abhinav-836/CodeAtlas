"""
CRUD operations for database models.
"""
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, asc, func, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, timedelta
import uuid

from app.db.models import (
    User, Analysis, Report, Finding, Language, 
    Export, ApiKeyUsage, Setting, Webhook,
    TaskStatus, RiskLevel, FindingSeverity  # Added FindingSeverity
)
from app.core.security import get_password_hash, verify_password


# ===== USER CRUD =====
async def create_user(
    db: AsyncSession,
    email: str,
    api_key: str,
    password: Optional[str] = None,
    **kwargs
) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(password) if password else None
    
    user = User(
        email=email,
        api_key=api_key,
        hashed_password=hashed_password,
        **kwargs
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_api_key(db: AsyncSession, api_key: str) -> Optional[User]:
    """Get user by API key."""
    result = await db.execute(
        select(User).where(User.api_key == api_key)
    )
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession,
    user_id: int,
    **kwargs
) -> Optional[User]:
    """Update user."""
    user = await get_user(db, user_id)
    if not user:
        return None
    
    for key, value in kwargs.items():
        if hasattr(user, key):
            if key == 'password' and value:
                user.hashed_password = get_password_hash(value)
            else:
                setattr(user, key, value)
    
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete user."""
    user = await get_user(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str
) -> Optional[User]:
    """Authenticate user with email and password."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ===== ANALYSIS CRUD =====
async def create_analysis(
    db: AsyncSession,
    repo_path: str,
    user_id: Optional[int] = None,
    **kwargs
) -> Analysis:
    """Create a new analysis."""
    analysis = Analysis(
        analysis_id=str(uuid.uuid4()),
        repo_path=repo_path,
        user_id=user_id,
        **kwargs
    )
    
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def get_analysis(
    db: AsyncSession,
    analysis_id: Union[int, str],
    include_report: bool = False
) -> Optional[Analysis]:
    """Get analysis by ID or analysis_id."""
    query = select(Analysis)
    
    if isinstance(analysis_id, int):
        query = query.where(Analysis.id == analysis_id)
    else:
        query = query.where(Analysis.analysis_id == analysis_id)
    
    if include_report:
        query = query.options(joinedload(Analysis.report))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_analyses(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    risk_level: Optional[RiskLevel] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "created_at",
    order_desc: bool = True
) -> List[Analysis]:
    """Get analyses with filters."""
    query = select(Analysis)
    
    # Apply filters
    if user_id:
        query = query.where(Analysis.user_id == user_id)
    if status:
        query = query.where(Analysis.status == status)
    if risk_level:
        query = query.where(Analysis.risk_level == risk_level)
    
    # Apply ordering
    order_column = getattr(Analysis, order_by, Analysis.created_at)
    if order_desc:
        query = query.order_by(desc(order_column))
    else:
        query = query.order_by(asc(order_column))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def update_analysis(
    db: AsyncSession,
    analysis_id: Union[int, str],
    **kwargs
) -> Optional[Analysis]:
    """Update analysis."""
    analysis = await get_analysis(db, analysis_id)
    if not analysis:
        return None
    
    for key, value in kwargs.items():
        if hasattr(analysis, key):
            setattr(analysis, key, value)
    
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def delete_analysis(db: AsyncSession, analysis_id: Union[int, str]) -> bool:
    """Delete analysis and associated data."""
    analysis = await get_analysis(db, analysis_id)
    if not analysis:
        return False
    
    await db.delete(analysis)
    await db.commit()
    return True


async def get_analysis_stats(
    db: AsyncSession,
    user_id: Optional[int] = None,
    days: int = 30
) -> Dict[str, Any]:
    """Get analysis statistics."""
    # Date cutoff
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Base query
    query = select(Analysis).where(Analysis.created_at >= cutoff)
    
    if user_id:
        query = query.where(Analysis.user_id == user_id)
    
    # Get all analyses
    result = await db.execute(query)
    analyses = result.scalars().all()
    
    if not analyses:
        return {
            "total": 0,
            "by_status": {},
            "by_risk": {},
            "average_duration": 0,
            "average_file_count": 0,
        }
    
    # Calculate stats
    total = len(analyses)
    by_status = {}
    by_risk = {}
    total_duration = 0
    total_files = 0
    completed_count = 0
    
    for analysis in analyses:
        # Status distribution
        status_value = analysis.status.value if analysis.status else "unknown"
        by_status[status_value] = by_status.get(status_value, 0) + 1
        
        # Risk distribution
        risk_value = analysis.risk_level.value if analysis.risk_level else "unknown"
        by_risk[risk_value] = by_risk.get(risk_value, 0) + 1
        
        # Averages
        if analysis.duration_seconds:
            total_duration += analysis.duration_seconds
            completed_count += 1
        
        if analysis.file_count:
            total_files += analysis.file_count
    
    return {
        "total": total,
        "by_status": by_status,
        "by_risk": by_risk,
        "average_duration": total_duration / completed_count if completed_count > 0 else 0,
        "average_file_count": total_files / total if total > 0 else 0,
        "period_days": days,
    }


# ===== REPORT CRUD =====
async def create_report(
    db: AsyncSession,
    analysis_id: Union[int, str],
    report_data: Dict[str, Any],
    user_id: Optional[int] = None
) -> Report:
    """Create a report for analysis."""
    # Get analysis
    analysis = await get_analysis(db, analysis_id)
    if not analysis:
        raise ValueError(f"Analysis {analysis_id} not found")
    
    report = Report(
        report_id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        user_id=user_id or analysis.user_id,
        summary=report_data.get("summary"),
        metrics=report_data.get("metrics"),
        architecture=report_data.get("architecture"),
        security=report_data.get("security"),
        python_analysis=report_data.get("python_analysis"),
        ai_insights=report_data.get("ai_insights"),
        expires_at=datetime.utcnow() + timedelta(days=30),  # Auto-expire in 30 days
    )
    
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_report(
    db: AsyncSession,
    report_id: Union[int, str],
    include_analysis: bool = False
) -> Optional[Report]:
    """Get report by ID or report_id."""
    query = select(Report)
    
    if isinstance(report_id, int):
        query = query.where(Report.id == report_id)
    else:
        query = query.where(Report.report_id == report_id)
    
    if include_analysis:
        query = query.options(joinedload(Report.analysis))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def search_reports(
    db: AsyncSession,
    query_str: Optional[str] = None,
    risk_level: Optional[RiskLevel] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Report]:
    """Search reports with filters."""
    stmt = select(Report).join(Analysis)
    
    # Apply filters
    if user_id:
        stmt = stmt.where(Report.user_id == user_id)
    
    if query_str:
        # Simple text search in summary
        stmt = stmt.where(
            or_(
                Report.summary.ilike(f"%{query_str}%"),
                Analysis.repo_path.ilike(f"%{query_str}%"),
            )
        )
    
    if risk_level:
        stmt = stmt.where(Analysis.risk_level == risk_level)
    
    if min_score is not None:
        stmt = stmt.where(Analysis.risk_score >= min_score)
    
    if max_score is not None:
        stmt = stmt.where(Analysis.risk_score <= max_score)
    
    if date_from:
        stmt = stmt.where(Report.created_at >= date_from)
    
    if date_to:
        stmt = stmt.where(Report.created_at <= date_to)
    
    # Order and paginate
    stmt = stmt.order_by(desc(Report.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_report(
    db: AsyncSession,
    report_id: Union[int, str],
    **kwargs
) -> Optional[Report]:
    """Update report."""
    report = await get_report(db, report_id)
    if not report:
        return None
    
    for key, value in kwargs.items():
        if hasattr(report, key):
            setattr(report, key, value)
    
    report.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(report)
    return report


# ===== FINDINGS CRUD =====
async def create_finding(
    db: AsyncSession,
    analysis_id: Union[int, str],
    finding_data: Dict[str, Any]
) -> Finding:
    """Create a finding for analysis."""
    analysis = await get_analysis(db, analysis_id)
    if not analysis:
        raise ValueError(f"Analysis {analysis_id} not found")
    
    finding = Finding(
        analysis_id=analysis.id,
        **finding_data
    )
    
    db.add(finding)
    await db.commit()
    await db.refresh(finding)
    return finding


async def get_findings(
    db: AsyncSession,
    analysis_id: Union[int, str],
    type_filter: Optional[str] = None,
    severity_filter: Optional[FindingSeverity] = None,
    limit: int = 1000
) -> List[Finding]:
    """Get findings for analysis."""
    analysis = await get_analysis(db, analysis_id)
    if not analysis:
        return []
    
    stmt = select(Finding).where(Finding.analysis_id == analysis.id)
    
    if type_filter:
        stmt = stmt.where(Finding.type == type_filter)
    
    if severity_filter:
        stmt = stmt.where(Finding.severity == severity_filter)
    
    stmt = stmt.order_by(
        desc(Finding.risk_score),
        desc(Finding.severity)
    ).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()


# ===== EXPORT CRUD =====
async def create_export(
    db: AsyncSession,
    report_id: Union[int, str],
    format: str,
    file_path: str,
    user_id: Optional[int] = None,
    expires_hours: int = 24
) -> Export:
    """Create an export record."""
    report = await get_report(db, report_id)
    if not report:
        raise ValueError(f"Report {report_id} not found")
    
    export = Export(
        export_id=str(uuid.uuid4()),
        report_id=report.id,
        user_id=user_id or report.user_id,
        format=format,
        file_path=file_path,
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )
    
    db.add(export)
    await db.commit()
    await db.refresh(export)
    return export


async def cleanup_expired_exports(db: AsyncSession) -> int:
    """Clean up expired exports."""
    stmt = delete(Export).where(
        Export.expires_at <= datetime.utcnow()
    )
    
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


# ===== SETTINGS CRUD =====
async def get_setting(db: AsyncSession, key: str) -> Optional[Setting]:
    """Get setting by key."""
    result = await db.execute(
        select(Setting).where(Setting.key == key)
    )
    return result.scalar_one_or_none()


async def set_setting(
    db: AsyncSession,
    key: str,
    value: Any,
    description: Optional[str] = None
) -> Setting:
    """Set or update a setting."""
    setting = await get_setting(db, key)
    
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = Setting(
            key=key,
            value=value,
            description=description
        )
        db.add(setting)
    
    await db.commit()
    await db.refresh(setting)
    return setting


async def delete_setting(db: AsyncSession, key: str) -> bool:
    """Delete a setting."""
    setting = await get_setting(db, key)
    if not setting:
        return False
    
    await db.delete(setting)
    await db.commit()
    return True


# ===== WEBHOOK CRUD =====
async def create_webhook(
    db: AsyncSession,
    user_id: int,
    url: str,
    name: str,
    events: List[str],
    secret: Optional[str] = None
) -> Webhook:
    """Create a webhook."""
    webhook = Webhook(
        user_id=user_id,
        url=url,
        name=name,
        events=events,
        secret=secret,
    )
    
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


async def get_webhooks_for_event(
    db: AsyncSession,
    event: str,
    active_only: bool = True
) -> List[Webhook]:
    """Get webhooks subscribed to an event."""
    stmt = select(Webhook)
    
    if active_only:
        stmt = stmt.where(Webhook.is_active == True)
    
    result = await db.execute(stmt)
    webhooks = result.scalars().all()
    
    # Filter by events (stored as JSON array)
    return [wh for wh in webhooks if event in wh.events]