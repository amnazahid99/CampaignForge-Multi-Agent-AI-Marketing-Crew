import logging
from typing import List, Dict, Any
from datetime import datetime

from backend.models import Campaign, EvaluationResult, CampaignState
from backend.quality_checks import DeterministicQualityChecker

logger = logging.getLogger(__name__)


class Evaluator:
    def __init__(self):
        self.results: List[EvaluationResult] = []

    def evaluate_campaign(self, campaign: Campaign) -> List[EvaluationResult]:
        self.results = []
        self._evaluate_research(campaign)
        self._evaluate_copy(campaign)
        self._evaluate_editor(campaign)
        self._evaluate_workflow(campaign)
        return self.results

    def _evaluate_research(self, campaign: Campaign):
        if campaign.research_report:
            sources = campaign.research_report.sources
            self.results.append(EvaluationResult(
                component="research",
                metric="source_validity",
                score=min(len(sources), 10),
                max_score=10,
                notes=f"{len(sources)} sources found.",
            ))
            self.results.append(EvaluationResult(
                component="research",
                metric="keyword_coverage",
                score=min(len(campaign.research_report.keyword_opportunities), 15),
                max_score=15,
            ))
            self.results.append(EvaluationResult(
                component="research",
                metric="competitor_coverage",
                score=min(len(campaign.research_report.competitor_messaging), 5),
                max_score=5,
            ))
        else:
            self.results.append(EvaluationResult(component="research", metric="completeness", score=0, max_score=10, notes="No research report."))

    def _evaluate_copy(self, campaign: Campaign):
        if not campaign.copy_variants:
            self.results.append(EvaluationResult(component="copywriter", metric="variant_count", score=0, max_score=10, notes="No variants."))
            return
        self.results.append(EvaluationResult(
            component="copywriter",
            metric="variant_count",
            score=min(len(campaign.copy_variants), 10),
            max_score=10,
            notes=f"{len(campaign.copy_variants)} variants generated.",
        ))
        brand_alignment = sum(1 for v in campaign.copy_variants if v.headline and v.primary_text)
        self.results.append(EvaluationResult(
            component="copywriter",
            metric="brand_alignment",
            score=brand_alignment,
            max_score=len(campaign.copy_variants),
        ))

    def _evaluate_editor(self, campaign: Campaign):
        if not campaign.editorial_review:
            self.results.append(EvaluationResult(component="editor", metric="review_completeness", score=0, max_score=10, notes="No editorial review."))
            return
        review = campaign.editorial_review
        self.results.append(EvaluationResult(
            component="editor",
            metric="review_score",
            score=review.overall_score,
            max_score=100,
            notes=f"Status: {review.status}",
        ))
        self.results.append(EvaluationResult(
            component="editor",
            metric="constraint_detection",
            score=10 - len([i for i in review.issues if i.check_type == "deterministic" and i.severity == "error"]),
            max_score=10,
        ))

    def _evaluate_workflow(self, campaign: Campaign):
        terminal_states = {CampaignState.PUBLISHED, CampaignState.READY_TO_PUBLISH, CampaignState.APPROVED, CampaignState.FAILED}
        if campaign.state in terminal_states:
            self.results.append(EvaluationResult(
                component="workflow",
                metric="completion_rate",
                score=100 if campaign.state in (CampaignState.PUBLISHED, CampaignState.READY_TO_PUBLISH) else 50,
                max_score=100,
                notes=f"State: {campaign.state.value}",
            ))
        else:
            self.results.append(EvaluationResult(component="workflow", metric="completion_rate", score=0, max_score=100, notes=f"Incomplete: {campaign.state.value}"))

        self.results.append(EvaluationResult(
            component="workflow",
            metric="revision_count",
            score=max(0, 10 - campaign.revision_count * 2),
            max_score=10,
            notes=f"Revisions: {campaign.revision_count}/{campaign.max_revisions}",
        ))
