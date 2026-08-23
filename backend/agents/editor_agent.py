import json
import logging
from typing import List, Optional, Dict, Any

from backend.models import CopyVariant, CampaignBrief, EditorialReview, EditorialIssue, CampaignState
from backend.quality_checks import DeterministicQualityChecker
from backend.config import config

logger = logging.getLogger(__name__)


class EditorAgent:
    def __init__(self):
        self.max_retries = config.MAX_CAMPAIGN_REVISIONS

    def evaluate(self, variants: List[CopyVariant], brief: CampaignBrief) -> EditorialReview:
        if not variants:
            return EditorialReview(
                status="REJECT",
                issues=[EditorialIssue(check_type="deterministic", severity="error", issue="No variants generated.", field="primary_text", required_action="Generate copy variants.")],
                revision_instructions=["Retry copy generation."],
                overall_score=0.0,
            )

        variant = variants[0]
        deterministic_issues = DeterministicQualityChecker.run_all_checks(variant, brief)

        ai_issues = self._ai_quality_review(variant, brief)

        all_issues = deterministic_issues + ai_issues
        errors = [i for i in all_issues if i.severity == "error"]
        warnings = [i for i in all_issues if i.severity == "warning"]

        status = "PASS" if not errors else "REJECT"
        revision_instructions = []
        if errors:
            revision_instructions.extend([i.required_action for i in errors if i.required_action])
        if warnings:
            revision_instructions.extend([i.required_action for i in warnings if i.required_action])

        score = self._compute_score(all_issues, variant)
        return EditorialReview(
            status=status,
            issues=all_issues,
            revision_instructions=list(dict.fromkeys(revision_instructions)),
            overall_score=score,
            deterministic_checks=[f"{i.field}: {i.issue}" for i in deterministic_issues],
            ai_checks=[f"{i.field}: {i.issue}" for i in ai_issues],
        )

    def _ai_quality_review(self, variant: CopyVariant, brief: CampaignBrief) -> List[EditorialIssue]:
        issues: List[EditorialIssue] = []
        text = f"{variant.headline} {variant.primary_text} {variant.cta}".lower()
        generic_phrases = ["best in class", "world-class", "seamless", "synergy", "leverage", "paradigm", "revolutionary"]
        for phrase in generic_phrases:
            if phrase in text:
                issues.append(EditorialIssue(
                    check_type="ai_derived",
                    severity="warning",
                    issue=f"Overly generic language detected: '{phrase}'.",
                    field="primary_text",
                    required_action=f"Replace '{phrase}' with a specific, product-related claim or verified brand statement.",
                ))
                break

        if len(variant.primary_text.split()) < 20:
            issues.append(EditorialIssue(
                check_type="ai_derived",
                severity="warning",
                issue="Primary text may be too short for effective messaging.",
                field="primary_text",
                required_action="Expand primary text with more detail or benefits.",
            ))

        if not variant.benefits:
            issues.append(EditorialIssue(
                check_type="ai_derived",
                severity="info",
                issue="No benefits listed.",
                field="benefits",
                required_action="Add 2-3 clear benefits aligned with the brief.",
            ))

        return issues

    def _compute_score(self, issues: List[EditorialIssue], variant: CopyVariant) -> float:
        if not issues:
            return 100.0
        deductions = 0.0
        for issue in issues:
            if issue.severity == "error":
                deductions += 20.0
            elif issue.severity == "warning":
                deductions += 5.0
            else:
                deductions += 1.0
        score = max(0.0, 100.0 - deductions)
        return round(score, 1)
