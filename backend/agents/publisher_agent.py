import json
import csv
import io
import logging
from typing import List, Dict, Any

from backend.models import Campaign, CampaignAsset, Platform

logger = logging.getLogger(__name__)


class PublisherAgent:
    def package(self, campaign: Campaign) -> List[CampaignAsset]:
        assets: List[CampaignAsset] = []
        for variant in campaign.approved_assets or campaign.copy_variants:
            content = self._format_variant(variant)
            assets.append(CampaignAsset(
                variant_id=variant.id,
                platform=variant.platform,
                content=content,
                metadata={
                    "framework": variant.framework.value,
                    "headline": variant.headline,
                    "cta": variant.cta,
                },
            ))
        return assets

    def _format_variant(self, variant) -> Dict[str, Any]:
        base = {
            "platform": variant.platform.value,
            "framework": variant.framework.value,
            "headline": variant.headline,
            "primary_text": variant.primary_text,
            "subheadline": variant.subheadline,
            "cta": variant.cta,
            "benefits": variant.benefits,
            "hashtags": variant.hashtags,
            "character_count": variant.character_count,
            "word_count": variant.word_count,
            "creative_direction": variant.creative_direction,
        }
        return base

    def export_json(self, assets: List[CampaignAsset], campaign_name: str) -> str:
        data = {
            "campaign_name": campaign_name,
            "assets": [a.model_dump() for a in assets],
        }
        return json.dumps(data, indent=2, default=str)

    def export_markdown(self, assets: List[CampaignAsset], campaign_name: str) -> str:
        lines = [f"# Campaign: {campaign_name}", ""]
        for asset in assets:
            lines.append(f"## {asset.platform.value}")
            lines.append("")
            c = asset.content
            lines.append(f"**Headline:** {c.get('headline', '')}")
            lines.append("")
            lines.append(f"**Primary Text:** {c.get('primary_text', '')}")
            lines.append("")
            if c.get("subheadline"):
                lines.append(f"**Subheadline:** {c['subheadline']}")
                lines.append("")
            lines.append(f"**CTA:** {c.get('cta', '')}")
            lines.append("")
            if c.get("benefits"):
                lines.append("**Benefits:**")
                for b in c["benefits"]:
                    lines.append(f"- {b}")
                lines.append("")
            if c.get("hashtags"):
                lines.append(f"**Hashtags:** {', '.join(c['hashtags'])}")
                lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    def export_csv(self, assets: List[CampaignAsset], campaign_name: str) -> str:
        output = io.StringIO()
        fieldnames = ["campaign_name", "platform", "framework", "headline", "primary_text", "cta", "character_count", "word_count"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for asset in assets:
            c = asset.content
            writer.writerow({
                "campaign_name": campaign_name,
                "platform": asset.platform.value,
                "framework": c.get("framework", ""),
                "headline": c.get("headline", ""),
                "primary_text": c.get("primary_text", ""),
                "cta": c.get("cta", ""),
                "character_count": c.get("character_count", 0),
                "word_count": c.get("word_count", 0),
            })
        return output.getvalue()
