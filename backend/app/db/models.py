"""
Database models for CodeAtlas.
"""
from sqlalchemy import (
    Column, Integer, String, Text, JSON, DateTime, 
    Boolean, Float, ForeignKey, Table, Enum, LargeBinary, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


# ===== ENUMERATIONS =====
class TaskStatus(str, enum.Enum):
    """Task status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class RiskLevel(str, enum.Enum):
    """Risk level enumeration."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingSeverity(str, enum.Enum):
    """Finding severity enumeration."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ===== ASSOCIATION TABLES =====
analysis_languages = Table(
    'analysis_languages',
    Base.metadata,
    Column('analysis_id', Integer, ForeignKey('analyses.id')),
    Column('language_id', Integer, ForeignKey('languages.id'))
)


# ===== MODELS =====
class User(Base):
    """User model for API access."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True)
    api_key = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255))
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    analyses = relationship("Analysis", back_populates="user")
    reports = relationship("Report", back_populates="user")


class Analysis(Base):
    """Analysis model for tracking repository analyses."""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    task_id = Column(String(36), unique=True, index=True)  # Task queue ID
    
    # Repository info
    repo_path = Column(Text, nullable=False)
    repo_name = Column(String(255))
    repo_url = Column(Text)
    branch = Column(String(100), default="main")
    
    # Analysis metadata
    status = Column(Enum(TaskStatus), default=TaskStatus.QUEUED, index=True)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.NONE, index=True)
    risk_score = Column(Float, default=0.0)
    
    # Statistics
    file_count = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    total_size_kb = Column(Float, default=0.0)
    duration_seconds = Column(Float)
    
    # Options
    options = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    user = relationship("User", back_populates="analyses")
    
    report = relationship("Report", uselist=False, back_populates="analysis")
    findings = relationship("Finding", back_populates="analysis")
    languages = relationship("Language", secondary=analysis_languages, back_populates="analyses")
    
    # Indexes
    __table_args__ = (
        Index('ix_analyses_user_status', 'user_id', 'status'),
        Index('ix_analyses_created_at', 'created_at'),
    )


class Report(Base):
    """Report model for storing analysis results."""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(36), unique=True, index=True, nullable=False)
    
    # Relationships
    analysis_id = Column(Integer, ForeignKey("analyses.id"), unique=True, index=True)
    analysis = relationship("Analysis", back_populates="report")
    
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    user = relationship("User", back_populates="reports")
    
    # Report data (can be large)
    summary = Column(JSON)  # Summary metrics
    metrics = Column(JSON)  # Detailed metrics
    architecture = Column(JSON)  # Architecture data
    security = Column(JSON)  # Security findings
    python_analysis = Column(JSON)  # Python-specific analysis
    ai_insights = Column(JSON)  # AI-generated insights
    
    # Export info
    has_json = Column(Boolean, default=False)
    has_html = Column(Boolean, default=False)
    has_pdf = Column(Boolean, default=False)
    has_markdown = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))  # For auto-cleanup
    
    # File storage info
    json_path = Column(Text)
    html_path = Column(Text)
    pdf_path = Column(Text)
    markdown_path = Column(Text)
    
    # Search optimization
    search_vector = Column(Text)  # For full-text search
    tags = Column(JSON, default=[])  # Custom tags


class Finding(Base):
    """Security/complexity findings from analysis."""
    __tablename__ = "findings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    analysis_id = Column(Integer, ForeignKey("analyses.id"), index=True)
    analysis = relationship("Analysis", back_populates="findings")
    
    # Finding details
    type = Column(String(50), index=True)  # 'secret', 'vulnerability', 'complexity'
    subtype = Column(String(100))  # 'API_KEY', 'SQL_INJECTION', etc.
    severity = Column(Enum(FindingSeverity), default=FindingSeverity.INFO, index=True)
    
    # Location
    file_path = Column(Text, nullable=False)
    line_number = Column(Integer)
    column = Column(Integer)
    
    # Content
    description = Column(Text)
    snippet = Column(Text)  # Code snippet
    context = Column(Text)  # Additional context
    
    # Risk assessment
    risk_score = Column(Float, default=0.0)
    is_false_positive = Column(Boolean, default=False)
    is_remediated = Column(Boolean, default=False)
    
    # Metadata
    detected_by = Column(String(100))  # Which scanner found it
    confidence = Column(Float, default=1.0)  # 0.0-1.0
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('ix_findings_analysis_type', 'analysis_id', 'type'),
        Index('ix_findings_severity_created', 'severity', 'created_at'),
    )


class Language(Base):
    """Programming languages detected in analyses."""
    __tablename__ = "languages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 'Python', 'JavaScript', etc.
    extension = Column(String(10))  # '.py', '.js'
    display_name = Column(String(100))
    color = Column(String(7))  # Hex color for UI
    
    # Relationships
    analyses = relationship("Analysis", secondary=analysis_languages, back_populates="languages")


class Export(Base):
    """Track export operations."""
    __tablename__ = "exports"
    
    id = Column(Integer, primary_key=True, index=True)
    export_id = Column(String(36), unique=True, index=True, nullable=False)
    
    # Relationships
    report_id = Column(Integer, ForeignKey("reports.id"), index=True)
    report = relationship("Report")
    
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    user = relationship("User")
    
    # Export details
    format = Column(String(20), nullable=False)  # 'json', 'html', 'pdf', 'markdown'
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer)  # Bytes
    download_count = Column(Integer, default=0)
    
    # Expiry
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    is_expired = Column(Boolean, default=False)
    
    # Status
    status = Column(String(20), default='ready')  # 'processing', 'ready', 'failed'
    error = Column(Text)


class ApiKeyUsage(Base):
    """Track API key usage for rate limiting and analytics."""
    __tablename__ = "api_key_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    user = relationship("User")
    
    # Usage details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    request_size = Column(Integer)
    response_size = Column(Integer)
    
    # Client info
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes for analytics
    __table_args__ = (
        Index('ix_apikeyusage_user_created', 'user_id', 'created_at'),
        Index('ix_apikeyusage_endpoint_created', 'endpoint', 'created_at'),
    )


class Setting(Base):
    """Application settings/key-value store."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON)
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))


class Webhook(Base):
    """Webhook configurations for integrations."""
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    user = relationship("User")
    
    # Webhook config
    name = Column(String(100), nullable=False)
    url = Column(Text, nullable=False)
    secret = Column(String(64))  # For HMAC validation
    events = Column(JSON, default=[])  # Events to listen for
    is_active = Column(Boolean, default=True)
    
    # Statistics
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_triggered = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())