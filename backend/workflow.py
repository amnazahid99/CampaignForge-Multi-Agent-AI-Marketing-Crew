import logging
from typing import Dict, Any, Optional
from datetime import datetime

from backend.models import CampaignBrief, CampaignState, Campaign, ResearchReport, PositioningReport, CopyVariant, EditorialReview, CampaignAsset
from backend.brand_kb import BrandKnowledgeBase
from backend.agents.research_agent import ResearchAgent
from backend.agents.copywriter_agent import CopywriterAgent
from backend.agents.editor_agent import EditorAgent
from backend.agents.publisher_agent import PublisherAgent
from backend.campaign_store import CampaignStore
from backend.config import config

logger = logging.getLogger(__name__)


class CampaignWorkflow:
    def __init__(self, brand_kb: BrandKnowledgeBase, store: CampaignStore):
        self.brand_kb = brand_kb
        self.store = store
        self.research_agent = ResearchAgent(brand_kb)
        self.copywriter_agent = CopywriterAgent(brand_kb)
        self.editor_agent = EditorAgent()
        self.publisher_agent = PublisherAgent()

    async def run(self, brief: CampaignBrief) -> Campaign:
        campaign = self.store.create(brief)
        try:
            campaign = await self._research_phase(campaign)
            if campaign.state == CampaignState.FAILED:
                return campaign
            campaign = await self._copywriting_phase(campaign)
            if campaign.state == CampaignState.FAILED:
                return campaign
            campaign = await self._editorial_phase(campaign)
            if campaign.state == CampaignState.FAILED:
                return campaign
            if campaign.editorial_review and campaign.editorial_review.status == "PASS":
                campaign = self._publisher_phase(campaign)
                campaign = self.store.mark_ready_to_publish(campaign.id)
            else:
                campaign = self.store.update_state(campaign.id, CampaignState.APPROVED)
            return campaign
        except Exception as e:
            logger.exception(f"Campaign workflow failed: {e}")
            campaign = self.store.update_state(campaign.id, CampaignState.FAILED, error=str(e))
            return campaign

    async def _research_phase(self, campaign: Campaign) -> Campaign:
        self.store.update_state(campaign.id, CampaignState.RESEARCHING)
        start = datetime.utcnow()
        try:
            research = await self.research_agent.execute(campaign.brief, campaign.id)
            positioning = self._derive_positioning(research, campaign.brief)
            campaign.research_report = research
            campaign.positioning_report = positioning
            campaign = self.store.update_research(campaign.id, research)
            campaign = self.store.update_positioning(campaign.id, positioning)
            campaign = self.store.update_state(campaign.id, CampaignState.RESEARCH_COMPLETE)
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self.store.append_log(campaign.id, {"agent": "research", "event": "complete", "duration_ms": duration})
            return campaign
        except Exception as e:
            logger.exception("Research phase failed")
            return self.store.update_state(campaign.id, CampaignState.FAILED, error=str(e))

    async def _copywriting_phase(self, campaign: Campaign) -> Campaign:
        self.store.update_state(campaign.id, CampaignState.COPYWRITING)
        start = datetime.utcnow()
        try:
            variants = await self.copywriter_agent.execute(campaign.brief, campaign.research_report, campaign.positioning_report, campaign)
            campaign.copy_variants = variants
            campaign = self.store.add_copy_variants(campaign.id, variants)
            campaign = self.store.update_state(campaign.id, CampaignState.EDITOR_REVIEW)
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self.store.append_log(campaign.id, {"agent": "copywriter", "event": "complete", "duration_ms": duration, "variants_generated": len(variants)})
            return campaign
        except Exception as e:
            logger.exception("Copywriting phase failed")
            return self.store.update_state(campaign.id, CampaignState.FAILED, error=str(e))

    async def _editorial_phase(self, campaign: Campaign) -> Campaign:
        self.store.update_state(campaign.id, CampaignState.EDITOR_REVIEW)
        start = datetime.utcnow()
        review = self.editor_agent.evaluate(campaign.copy_variants, campaign.brief)
        campaign = self.store.update_editorial_review(campaign.id, review)
        duration = (datetime.utcnow() - start).total_seconds() * 1000
        self.store.append_log(campaign.id, {"agent": "editor", "event": "evaluate", "duration_ms": duration, "status": review.status, "score": review.overall_score})

        if review.status == "REJECT" and campaign.revision_count < campaign.max_revisions:
            campaign.revision_count += 1
            campaign = self.store.update_state(campaign.id, CampaignState.REVISION_REQUIRED)
            return await self._revision_phase(campaign, review)
        return campaign

    async def _revision_phase(self, campaign: Campaign, review: EditorialReview) -> Campaign:
        self.store.update_state(campaign.id, CampaignState.COPYWRITING)
        start = datetime.utcnow()
        try:
            instructions = "\n".join(review.revision_instructions)
            brand_context = self.brand_kb.get_context(f"revision feedback: {instructions}", n_results=3)
            variants = await self.copywriter_agent.execute(campaign.brief, campaign.research_report, campaign.positioning_report, campaign)
            campaign.copy_variants = variants
            campaign = self.store.add_copy_variants(campaign.id, variants)
            review = self.editor_agent.evaluate(campaign.copy_variants, campaign.brief)
            campaign = self.store.update_editorial_review(campaign.id, review)
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self.store.append_log(campaign.id, {"agent": "copywriter", "event": "revision", "duration_ms": duration, "revision_count": campaign.revision_count, "status": review.status})
            if review.status == "PASS":
                campaign = self.store.update_state(campaign.id, CampaignState.EDITOR_REVIEW)
            else:
                campaign = self.store.update_state(campaign.id, CampaignState.FAILED, error="Max revisions exceeded or editorial rejection.")
            return campaign
        except Exception as e:
            logger.exception("Revision phase failed")
            return self.store.update_state(campaign.id, CampaignState.FAILED, error=str(e))

    def _publisher_phase(self, campaign: Campaign) -> Campaign:
        start = datetime.utcnow()
        try:
            assets = self.publisher_agent.package(campaign)
            campaign.approved_assets = assets
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self.store.append_log(campaign.id, {"agent": "publisher", "event": "package", "duration_ms": duration, "assets_count": len(assets)})
            return campaign
        except Exception as e:
            logger.exception("Publisher phase failed")
            return self.store.update_state(campaign.id, CampaignState.FAILED, error=str(e))

    def _derive_positioning(self, research: ResearchReport, brief: CampaignBrief) -> PositioningReport:
        return PositioningReport(
            summary=research.market_position,
            market_position=research.market_position,
            target_audience_insights=research.target_audience_insights,
            pain_points=research.pain_points,
            competitor_messaging=research.competitor_messaging,
            market_trends=research.market_trends,
            keyword_opportunities=research.keyword_opportunities,
            differentiation_opportunities=research.differentiation_opportunities,
            risks=research.risks,
            sources=research.sources,
        )

    async def revise_after_editorial(self, campaign_id: str) -> Optional[Campaign]:
        campaign = self.store.get(campaign_id)
        if not campaign or not campaign.editorial_review:
            return None
        return await self._revision_phase(campaign, campaign.editorial_review)

    async def human_approve(self, campaign_id: str) -> Optional[Campaign]:
        campaign = self.store.get(campaign_id)
        if not campaign:
            return None
        if campaign.editorial_review and campaign.editorial_review.status == "PASS":
            campaign = self._publisher_phase(campaign)
            return self.store.mark_ready_to_publish(campaign.id)
        return campaign

    def human_reject(self, campaign_id: str, reason: str = "") -> Optional[Campaign]:
        campaign = self.store.get(campaign_id)
        if not campaign:
            return None
        return self.store.update_state(campaign_id, CampaignState.DRAFT, error=f"Human rejection: {reason}")
