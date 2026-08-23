import pytest
import json
from backend.models import CampaignBrief, CampaignState, CopyVariant, Platform, CopyFramework, EditorialIssue, ResearchReport
from backend.quality_checks import DeterministicQualityChecker
from backend.campaign_store import CampaignStore
from backend.quality_checks import DeterministicQualityChecker
from backend.evaluator import Evaluator
from backend.brand_kb import BrandKnowledgeBase
from backend.vector_store import VectorStore
from backend.config import config


@pytest.fixture
def tmp_store(tmp_path):
    return CampaignStore(str(tmp_path / "campaigns"))


@pytest.fixture
def sample_brief():
    return CampaignBrief(
        product_service="AI Productivity Platform",
        product_description="Automate tasks for small businesses.",
        target_audience="Small business owners",
        campaign_objective="Generate qualified leads",
        target_market="North America",
        preferred_channels=["LinkedIn", "Instagram", "X/Twitter"],
        tone="Professional, confident, human",
        key_selling_points=["Save 10+ hours/week", "Increase retention 25%"],
        cta="Book a demo",
        campaign_duration="4 weeks",
        competitor_names=["CompetitorA", "CompetitorB"],
    )


def test_campaign_store_create_and_get(tmp_store, sample_brief):
    campaign = tmp_store.create(sample_brief)
    assert campaign.id
    assert campaign.state == CampaignState.DRAFT
    fetched = tmp_store.get(campaign.id)
    assert fetched is not None
    assert fetched.name == "AI Productivity Platform"


def test_campaign_store_state_transitions(tmp_store, sample_brief):
    campaign = tmp_store.create(sample_brief)
    tmp_store.update_state(campaign.id, CampaignState.RESEARCHING)
    updated = tmp_store.get(campaign.id)
    assert updated.state == CampaignState.RESEARCHING


def test_deterministic_checks_missing_fields():
    variant = CopyVariant(id="v1", platform=Platform.LINKEDIN, framework=CopyFramework.AIDA, headline="", primary_text="", cta="")
    issues = DeterministicQualityChecker.run_all_checks(variant, CampaignBrief(
        product_service="X", product_description="X", target_audience="Y", campaign_objective="Z", target_market="US", cta="Buy"
    ))
    assert any(i.field == "headline" and i.severity == "error" for i in issues)
    assert any(i.field == "primary_text" and i.severity == "error" for i in issues)
    assert any(i.field == "cta" and i.severity == "error" for i in issues)


def test_deterministic_checks_platform_limits():
    long_text = "x" * 5000
    variant = CopyVariant(id="v1", platform=Platform.X, framework=CopyFramework.AIDA, headline="Hi", primary_text=long_text, cta="Buy")
    brief = CampaignBrief(product_service="X", product_description="X", target_audience="Y", campaign_objective="Z", target_market="US", cta="Buy")
    issues = DeterministicQualityChecker.run_all_checks(variant, brief)
    assert any(i.field == "primary_text" and i.severity == "error" for i in issues)


def test_evaluator_produces_results(tmp_store, sample_brief):
    campaign = tmp_store.create(sample_brief)
    campaign.research_report = ResearchReport(market_position="test", sources=["s1"])
    campaign.positioning_report = None
    campaign.copy_variants = [CopyVariant(id="v1", platform=Platform.LINKEDIN, framework=CopyFramework.AIDA, headline="H", primary_text="Some text", cta="Buy")]
    campaign.editorial_review = None
    evaluator = Evaluator()
    results = evaluator.evaluate_campaign(campaign)
    assert len(results) > 0
    assert any(r.component == "workflow" for r in results)


def test_brand_kb_add_and_retrieve(tmp_path):
    vs = VectorStore(str(tmp_path / "faiss"), config.EMBEDDING_MODEL, 5)
    kb = BrandKnowledgeBase(vs)
    doc = kb.add_document("test.txt", "Our product saves time and increases efficiency.")
    assert doc.chunk_count > 0
    results = kb.retrieve("product saves time", n_results=2)
    assert len(results) > 0
    assert results[0]["source"] == "test.txt"
