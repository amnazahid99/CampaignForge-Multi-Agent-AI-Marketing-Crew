import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from backend.models import CampaignBrief, ResearchReport, CopyVariant, CopyFramework, Platform, Campaign
from backend.brand_kb import BrandKnowledgeBase
from backend.config import config

logger = logging.getLogger(__name__)


class CopywriterAgent:
    def __init__(self, brand_kb: BrandKnowledgeBase):
        self.brand_kb = brand_kb
        self.max_retries = config.MAX_CAMPAIGN_REVISIONS

    async def execute(self, brief: CampaignBrief, research: Optional[ResearchReport], positioning, campaign: Campaign) -> List[CopyVariant]:
        brand_context = self.brand_kb.retrieve_for_brief(brief, n_results=6)
        brand_context_str = "\n\n".join([f"[{r['source']}]\n{r['text']}" for r in brand_context])

        frameworks = [CopyFramework.AIDA, CopyFramework.PAS, CopyFramework.FAB, CopyFramework.BAB]
        platforms = [Platform(p) for p in brief.preferred_channels]
        variants: List[CopyVariant] = []
        seen_ids = set()

        for platform in platforms:
            for framework in frameworks:
                variant = await self._generate_variant(brief, research, positioning, brand_context_str, platform, framework, campaign)
                if variant and variant.id not in seen_ids:
                    variants.append(variant)
                    seen_ids.add(variant.id)
        return variants

    async def _generate_variant(self, brief, research, positioning, brand_context: str, platform: Platform, framework: CopyFramework, campaign: Campaign) -> Optional[CopyVariant]:
        try:
            prompt = self._build_prompt(brief, research, positioning, brand_context, self._extract_brand_claims(brand_context), platform, framework)
            import ollama
            client = ollama.Client(host=config.OLLAMA_HOST)
            response = client.chat(
                model=config.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_predict": 1024},
            )
            content = response["message"]["content"]
            variant = self._parse_variant(content, platform, framework, brief)
            if variant and variant.headline and variant.primary_text:
                return variant
        except Exception as e:
            logger.warning(f"LLM copy generation failed for {platform.value}/{framework.value}: {e}")
        return self._generate_demo_variant(brief, platform, framework)

    def _generate_demo_variant(self, brief, platform: Platform, framework: CopyFramework) -> CopyVariant:
        audience = brief.target_audience.split(",")[0].strip() if brief.target_audience else "your audience"
        benefits = brief.key_selling_points or ["Save time", "Increase retention"]
        benefits_text = "; ".join(benefits[:2])
        headline = f"Transform Your {audience} Workflow"
        primary_text = f"Stop wasting time on manual tasks. Our platform helps {audience} automate workflows with {benefits_text}. {brief.cta} today."
        return CopyVariant(
            id=f"variant_{platform.value.lower().replace('/', '_')}_{framework.value.lower()}_demo",
            platform=platform,
            framework=framework,
            headline=headline,
            primary_text=primary_text,
            cta=brief.cta,
            benefits=benefits,
            hashtags=["#AI", "#Productivity", "#Automation"],
            character_count=len(primary_text),
            word_count=len(primary_text.split()),
            creative_direction=f"Demo variant using {framework.value} framework",
            notes="Generated in demo mode due to unavailable LLM.",
        )

    def _build_prompt(self, brief, research, positioning, brand_context: str, brand_claims: List[str], platform: Platform, framework: CopyFramework) -> str:
        claims_text = "\n".join([f"- {c}" for c in brand_claims[:10]]) if brand_claims else "No approved claims retrieved. Use only verified information."
        return f"""You are a professional copywriter. Generate a marketing campaign variant.

Product/Service: {brief.product_service}
Description: {brief.product_description}
Target Audience: {brief.target_audience}
Objective: {brief.campaign_objective}
Tone: {brief.tone}
CTA: {brief.cta}
Channels: {', '.join(brief.preferred_channels)}
Platform: {platform.value}
Framework: {framework.value}
Key Selling Points: {', '.join(brief.key_selling_points)}

Approved Brand Claims (DO NOT invent new claims):
{claims_text}

Brand Context (do not quote directly, use for alignment):
{brand_context[:2000]}

Research Context:
{research.market_position if research else 'N/A'}

Generate copy with these fields in JSON:
{{
  "headline": "...",
  "primary_text": "...",
  "subheadline": "...",
  "cta": "...",
  "benefits": ["..."],
  "hashtags": ["..."],
  "creative_direction": "...",
  "notes": "..."
}}

Rules:
- Use only the approved brand claims or clearly generic statements.
- Do not invent product features, statistics, or testimonials.
- Match the specified tone and target audience.
- Optimize for {platform.value}.
- Ensure headline is punchy and CTA is clear.
- Do not exceed {platform.value} character limits.
- Return ONLY valid JSON. No extra text.
"""

    def _extract_brand_claims(self, brand_context: str) -> List[str]:
        claims: List[str] = []
        for line in brand_context.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                claims.append(line.lstrip("-* ").strip())
        return claims[:20]

    def _parse_variant(self, content: str, platform: Platform, framework: CopyFramework, brief: CampaignBrief) -> Optional[CopyVariant]:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end == -1:
                return None
            data = json.loads(content[start:end])
            headline = data.get("headline", "")
            primary_text = data.get("primary_text", "")
            if not headline or not primary_text:
                return None
            return CopyVariant(
                id=f"variant_{platform.value.lower().replace('/', '_')}_{framework.value.lower()}",
                platform=platform,
                framework=framework,
                headline=headline,
                primary_text=primary_text,
                subheadline=data.get("subheadline"),
                benefits=data.get("benefits", []),
                cta=data.get("cta", brief.cta),
                hashtags=data.get("hashtags", []),
                character_count=len(primary_text),
                word_count=len(primary_text.split()),
                creative_direction=data.get("creative_direction", ""),
                notes=data.get("notes", ""),
            )
        except Exception:
            return None
