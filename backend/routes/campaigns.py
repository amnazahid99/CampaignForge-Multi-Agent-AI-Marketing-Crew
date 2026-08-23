import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
import os

from backend.models import CampaignBrief, Campaign, CampaignState, EditorialReview, CopyVariant, CampaignAsset
from backend.workflow import CampaignWorkflow
from backend.brand_kb import BrandKnowledgeBase
from backend.campaign_store import CampaignStore
from backend.config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["campaigns"])

_workflow: Optional[CampaignWorkflow] = None
_store: Optional[CampaignStore] = None


def init_workflow(workflow: CampaignWorkflow, store: CampaignStore):
    global _workflow, _store
    _workflow = workflow
    _store = store


@router.post("/")
async def create_campaign(brief: CampaignBrief):
    if not _workflow or not _store:
        raise HTTPException(status_code=500, detail="Workflow not initialized")
    campaign = await _workflow.run(brief)
    return campaign.model_dump(mode="json")


@router.get("/")
async def list_campaigns():
    if not _store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    campaigns = _store.list_all()
    return [c.model_dump(mode="json") for c in campaigns]


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    if not _store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    campaign = _store.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign.model_dump(mode="json")


@router.post("/{campaign_id}/approve")
async def approve_campaign(campaign_id: str):
    if not _workflow:
        raise HTTPException(status_code=500, detail="Workflow not initialized")
    campaign = await _workflow.human_approve(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign.model_dump(mode="json")


@router.post("/{campaign_id}/reject")
async def reject_campaign(campaign_id: str, reason: str = ""):
    if not _workflow:
        raise HTTPException(status_code=500, detail="Workflow not initialized")
    campaign = _workflow.human_reject(campaign_id, reason)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign.model_dump(mode="json")


@router.post("/{campaign_id}/revise")
async def revise_campaign(campaign_id: str):
    if not _workflow:
        raise HTTPException(status_code=500, detail="Workflow not initialized")
    campaign = await _workflow.revise_after_editorial(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign.model_dump(mode="json")
