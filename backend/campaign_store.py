import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from backend.models import Campaign, CampaignState


class CampaignStore:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._campaigns: Dict[str, Campaign] = {}
        self._load_all()

    def _load_all(self):
        for f in self.base_path.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    campaign = Campaign.model_validate(data)
                    self._campaigns[campaign.id] = campaign
            except Exception:
                continue

    def _save(self, campaign: Campaign):
        path = self.base_path / f"{campaign.id}.json"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(campaign.model_dump_json(indent=2))

    def create(self, brief) -> Campaign:
        campaign_id = f"campaign_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        campaign = Campaign(id=campaign_id, name=brief.product_service, brief=brief)
        self._campaigns[campaign_id] = campaign
        self._save(campaign)
        return campaign

    def get(self, campaign_id: str) -> Optional[Campaign]:
        return self._campaigns.get(campaign_id)

    def list_all(self) -> List[Campaign]:
        return sorted(self._campaigns.values(), key=lambda c: c.created_at, reverse=True)

    def update_state(self, campaign_id: str, state: CampaignState, error: Optional[str] = None):
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.state = state
            campaign.updated_at = datetime.utcnow()
            if error:
                campaign.error = error
            self._save(campaign)
        return campaign

    def append_log(self, campaign_id: str, log: Dict[str, Any]):
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.logs.append(log)
            campaign.updated_at = datetime.utcnow()
            self._save(campaign)

    def update_research(self, campaign_id: str, research):
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.research_report = research
            campaign.updated_at = datetime.utcnow()
            self._save(campaign)
        return campaign

    def update_positioning(self, campaign_id: str, positioning):
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.positioning_report = positioning
            campaign.updated_at = datetime.utcnow()
            self._save(campaign)
        return campaign

    def add_copy_variants(self, campaign_id: str, variants):
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.copy_variants.extend(variants)
            campaign.updated_at = datetime.utcnow()
            self._save(campaign)
        return campaign

    def update_editorial_review(self, campaign_id: str, review):
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.editorial_review = review
            campaign.updated_at = datetime.utcnow()
            self._save(campaign)
        return campaign

    def approve(self, campaign_id: str) -> Optional[Campaign]:
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.state = CampaignState.APPROVED
            campaign.updated_at = datetime.utcnow()
            self._save(campaign)
            return campaign
        return None

    def mark_ready_to_publish(self, campaign_id: str) -> Optional[Campaign]:
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.state = CampaignState.READY_TO_PUBLISH
            campaign.updated_at = datetime.utcnow()
            self._save(campaign)
            return campaign
        return None

    def mark_published(self, campaign_id: str) -> Optional[Campaign]:
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.state = CampaignState.PUBLISHED
            campaign.completed_at = datetime.utcnow()
            campaign.updated_at = datetime.utcnow()
            self._save(campaign)
            return campaign
        return None

    def delete(self, campaign_id: str) -> bool:
        if campaign_id in self._campaigns:
            del self._campaigns[campaign_id]
            path = self.base_path / f"{campaign_id}.json"
            if path.exists():
                path.unlink()
            return True
        return False
