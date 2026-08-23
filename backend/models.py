from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from datetime import datetime


class Course(BaseModel):
    title: str
    course_link: Optional[str] = None
    instructor: Optional[str] = None
    lessons: List['Lesson'] = []


class Lesson(BaseModel):
    lesson_number: int
    title: str
    lesson_link: Optional[str] = None


class CourseChunk(BaseModel):
    content: str
    course_title: str
    lesson_number: Optional[int] = None
    chunk_index: int


class CampaignState(str, Enum):
    DRAFT = "DRAFT"
    RESEARCHING = "RESEARCHING"
    RESEARCH_COMPLETE = "RESEARCH_COMPLETE"
    COPYWRITING = "COPYWRITING"
    EDITOR_REVIEW = "EDITOR_REVIEW"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    APPROVED = "APPROVED"
    READY_TO_PUBLISH = "READY_TO_PUBLISH"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class CampaignBrief(BaseModel):
    product_service: str = Field(..., description="Name of the product or service")
    product_description: str = Field(..., description="Detailed product/service description")
    target_audience: str = Field(..., description="Primary target audience")
    campaign_objective: str = Field(..., description="Primary campaign objective")
    target_market: str = Field(..., description="Target market or location")
    preferred_channels: List[str] = Field(default_factory=lambda: ["LinkedIn", "Instagram", "X/Twitter"])
    tone: str = Field(default="Professional, confident, human")
    key_selling_points: List[str] = Field(default_factory=list)
    cta: str = Field(..., description="Call to action")
    campaign_duration: str = Field(default="4 weeks")
    competitor_names: List[str] = Field(default_factory=list)
    brand_guidelines: Optional[str] = None
    brand_documents: List[str] = Field(default_factory=list, description="Uploaded brand document filenames")


class ResearchReport(BaseModel):
    market_position: str = ""
    target_audience_insights: str = ""
    pain_points: List[str] = Field(default_factory=list)
    competitor_messaging: Dict[str, str] = Field(default_factory=dict)
    market_trends: List[str] = Field(default_factory=list)
    keyword_opportunities: List[str] = Field(default_factory=list)
    differentiation_opportunities: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    confidence: str = "medium"
    research_mode: str = "demo"


class CompetitorInsight(BaseModel):
    competitor_name: str
    positioning: str = ""
    messaging: str = ""
    value_propositions: List[str] = Field(default_factory=list)
    cta_patterns: List[str] = Field(default_factory=list)
    content_themes: List[str] = Field(default_factory=list)
    differentiation_opportunities: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)


class PositioningReport(BaseModel):
    summary: str = ""
    market_position: str = ""
    target_audience_insights: str = ""
    pain_points: List[str] = Field(default_factory=list)
    competitor_messaging: Dict[str, str] = Field(default_factory=dict)
    market_trends: List[str] = Field(default_factory=list)
    keyword_opportunities: List[str] = Field(default_factory=list)
    differentiation_opportunities: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


class CopyFramework(str, Enum):
    AIDA = "AIDA"
    PAS = "PAS"
    FAB = "FAB"
    BAB = "Before/After/Bridge"
    PROBLEM_SOLUTION = "Problem/Solution"


class Platform(str, Enum):
    LINKEDIN = "LinkedIn"
    INSTAGRAM = "Instagram"
    X = "X/Twitter"
    LANDING_PAGE = "Landing Page"
    EMAIL = "Email"
    ADS = "Advertising"


class CopyVariant(BaseModel):
    id: str
    platform: Platform
    framework: CopyFramework
    headline: str = ""
    primary_text: str = ""
    subheadline: Optional[str] = None
    benefits: List[str] = Field(default_factory=list)
    cta: str = ""
    hashtags: List[str] = Field(default_factory=list)
    character_count: int = 0
    word_count: int = 0
    creative_direction: str = ""
    notes: str = ""


class EditorialIssue(BaseModel):
    check_type: Literal["deterministic", "ai_derived"]
    severity: Literal["error", "warning", "info"]
    issue: str
    field: str
    required_action: Optional[str] = None


class EditorialReview(BaseModel):
    status: Literal["PASS", "REJECT"]
    issues: List[EditorialIssue] = Field(default_factory=list)
    revision_instructions: List[str] = Field(default_factory=list)
    overall_score: float = 0.0
    deterministic_checks: List[str] = Field(default_factory=list)
    ai_checks: List[str] = Field(default_factory=list)


class CampaignAsset(BaseModel):
    variant_id: str
    platform: Platform
    content: Dict[str, Any]
    export_formats: List[str] = Field(default_factory=lambda: ["json", "markdown"])
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Campaign(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str
    name: str
    state: CampaignState = CampaignState.DRAFT
    brief: CampaignBrief
    research_report: Optional[ResearchReport] = None
    positioning_report: Optional[PositioningReport] = None
    copy_variants: List[CopyVariant] = Field(default_factory=list)
    editorial_review: Optional[EditorialReview] = None
    approved_assets: List[CampaignAsset] = Field(default_factory=list)
    revision_count: int = 0
    max_revisions: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class AgentLogEntry(BaseModel):
    agent: str
    event: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class BrandDocument(BaseModel):
    filename: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    chunk_count: int = 0


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    confidence: str = "medium"


class EvaluationResult(BaseModel):
    component: str
    metric: str
    score: float
    max_score: float
    notes: str = ""
    measured: bool = True
