import logging
import json
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from backend.models import Campaign, CampaignState
from backend.workflow import CampaignWorkflow
from backend.campaign_store import CampaignStore
from backend.agents.publisher_agent import PublisherAgent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])

_store: Optional[CampaignStore] = None
_publisher: Optional[PublisherAgent] = None


def init_export(store: CampaignStore, publisher: PublisherAgent):
    global _store, _publisher
    _store = store
    _publisher = publisher


@router.get("/{campaign_id}/json")
async def export_json(campaign_id: str):
    campaign = _store.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.state not in (CampaignState.APPROVED, CampaignState.READY_TO_PUBLISH, CampaignState.PUBLISHED):
        raise HTTPException(status_code=400, detail="Campaign not approved for export")
    assets = _publisher.package(campaign)
    data = _publisher.export_json(assets, campaign.name)
    return PlainTextResponse(content=data, media_type="application/json")


@router.get("/{campaign_id}/markdown")
async def export_markdown(campaign_id: str):
    campaign = _store.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.state not in (CampaignState.APPROVED, CampaignState.READY_TO_PUBLISH, CampaignState.PUBLISHED):
        raise HTTPException(status_code=400, detail="Campaign not approved for export")
    assets = _publisher.package(campaign)
    data = _publisher.export_markdown(assets, campaign.name)
    return PlainTextResponse(content=data, media_type="text/markdown")


@router.get("/{campaign_id}/csv")
async def export_csv(campaign_id: str):
    campaign = _store.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.state not in (CampaignState.APPROVED, CampaignState.READY_TO_PUBLISH, CampaignState.PUBLISHED):
        raise HTTPException(status_code=400, detail="Campaign not approved for export")
    assets = _publisher.package(campaign)
    data = _publisher.export_csv(assets, campaign.name)
    return PlainTextResponse(content=data, media_type="text/csv")
