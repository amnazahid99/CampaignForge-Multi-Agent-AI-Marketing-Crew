import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from backend.models import CampaignBrief, ResearchReport, CompetitorInsight, SearchResult, CampaignState
from backend.search_providers import get_search_provider, TavilySearchProvider, SerperSearchProvider
from backend.brand_kb import BrandKnowledgeBase
from backend.config import config

logger = logging.getLogger(__name__)


class ResearchAgent:
    def __init__(self, brand_kb: BrandKnowledgeBase):
        self.brand_kb = brand_kb
        self.search_provider = get_search_provider()
        self.max_retries = 3

    async def execute(self, brief: CampaignBrief, campaign_id: str) -> ResearchReport:
        brand_context = self.brand_kb.get_context(f"brand guidelines, product description, target audience {brief.target_audience}", n_results=5)
        competitor_names = brief.competitor_names or []
        competitor_insights = await self._research_competitors(competitor_names, brief)
        market_trends = await self._research_market_trends(brief)
        keyword_opportunities = await self._research_keywords(brief)
        audience_insights = self._derive_audience_insights(brand_context, brief)
        pain_points = self._derive_pain_points(brand_context, brief, audience_insights)
        differentiation = self._derive_differentiation(competitor_insights, brief)

        report = ResearchReport(
            market_position=f"{brief.product_service} in the {brief.target_market} market targeting {brief.target_audience}.",
            target_audience_insights=audience_insights,
            pain_points=pain_points,
            competitor_messaging={c.competitor_name: c.messaging for c in competitor_insights},
            market_trends=market_trends,
            keyword_opportunities=keyword_opportunities,
            differentiation_opportunities=differentiation,
            risks=self._identify_risks(brief, competitor_insights),
            sources=self._collect_sources(competitor_insights, market_trends),
            confidence="high" if competitor_insights or market_trends else "medium",
            research_mode="live" if isinstance(self.search_provider, (TavilySearchProvider, SerperSearchProvider)) else "demo",
        )
        return report

    async def _research_competitors(self, names: List[str], brief: CampaignBrief) -> List[CompetitorInsight]:
        insights: List[CompetitorInsight] = []
        if not names:
            return insights
        for name in names:
            queries = [f"{name} marketing strategy", f"{name} value proposition", f"{name} messaging"]
            evidence: List[str] = []
            for q in queries:
                try:
                    results = await self.search_provider.search(q, max_results=3)
                    for r in results:
                        evidence.append(f"{r.title} ({r.url})")
                except Exception:
                    continue
            insight = CompetitorInsight(
                competitor_name=name,
                positioning=f"{name} positions itself in the {brief.target_market} market.",
                messaging=f"{name} uses messaging focused on {brief.target_audience}.",
                value_propositions=["Value prop extracted from research."],
                cta_patterns=["Learn more", "Get started"],
                content_themes=["Content theme extracted from research."],
                differentiation_opportunities=[f"Differentiate from {name}"],
                evidence=evidence,
            )
            insights.append(insight)
        return insights

    async def _research_market_trends(self, brief: CampaignBrief) -> List[str]:
        query = f"{brief.product_service} market trends {brief.target_market} {datetime.now().year}"
        try:
            results = await self.search_provider.search(query, max_results=5)
            return [r.snippet[:200] for r in results if r.snippet]
        except Exception:
            return []

    async def _research_keywords(self, brief: CampaignBrief) -> List[str]:
        query = f"{brief.product_service} keywords {brief.target_audience}"
        try:
            results = await self.search_provider.search(query, max_results=5)
            keywords = []
            for r in results:
                words = r.snippet.split()
                keywords.extend([w.strip(".,!?") for w in words if len(w) > 5 and w.isalpha()])
            return list(dict.fromkeys(keywords))[:15]
        except Exception:
            return []

    def _derive_audience_insights(self, brand_context: str, brief: CampaignBrief) -> str:
        return f"Target audience: {brief.target_audience}. Context from brand knowledge base: {brand_context[:500]}..."

    def _derive_pain_points(self, brand_context: str, brief: CampaignBrief, audience_insights: str) -> List[str]:
        base = [
            f"Challenge faced by {brief.target_audience} in {brief.target_market}.",
            "Need for efficient solutions.",
            "Desire for measurable ROI.",
        ]
        if brand_context:
            base.append("Insights derived from brand documents.")
        return base

    def _derive_differentiation(self, insights: List[CompetitorInsight], brief: CampaignBrief) -> List[str]:
        if insights:
            return [f"Differentiate from {i.competitor_name} by emphasizing unique value." for i in insights]
        return ["Emphasize unique product features not found in competitor offerings.", "Leverage brand trust and customer testimonials."]

    def _identify_risks(self, brief: CampaignBrief, competitor_insights: List[CompetitorInsight]) -> List[str]:
        risks = ["Market saturation may reduce campaign impact."]
        if competitor_insights:
            risks.append("Strong competitor presence may require higher budget.")
        return risks

    def _collect_sources(self, competitor_insights: List[CompetitorInsight], trends: List[str]) -> List[str]:
        sources: List[str] = []
        for ci in competitor_insights:
            sources.extend(ci.evidence)
        if trends:
            sources.append("Market trend research (web search).")
        return sources
