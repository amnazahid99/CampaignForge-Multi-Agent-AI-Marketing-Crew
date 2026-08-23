import re
from typing import List, Dict, Any, Tuple
from backend.models import CopyVariant, Platform, EditorialIssue, CampaignBrief


PLATFORM_LIMITS = {
    Platform.LINKEDIN: {"headline": 150, "primary_text": 3000, "cta": 50},
    Platform.INSTAGRAM: {"headline": 150, "primary_text": 2200, "cta": 50},
    Platform.X: {"headline": 100, "primary_text": 280, "cta": 50},
    Platform.LANDING_PAGE: {"headline": 100, "primary_text": 5000, "cta": 50},
    Platform.EMAIL: {"headline": 100, "primary_text": 5000, "cta": 50},
    Platform.ADS: {"headline": 100, "primary_text": 500, "cta": 50},
}


class DeterministicQualityChecker:
    @staticmethod
    def run_all_checks(variant: CopyVariant, brief: CampaignBrief) -> List[EditorialIssue]:
        issues: List[EditorialIssue] = []
        issues.extend(DeterministicQualityChecker.check_platform_limits(variant))
        issues.extend(DeterministicQualityChecker.check_required_fields(variant))
        issues.extend(DeterministicQualityChecker.check_cta_presence(variant, brief))
        issues.extend(DeterministicQualityChecker.check_duplicate_content(variant))
        issues.extend(DeterministicQualityChecker.check_readability(variant))
        issues.extend(DeterministicQualityChecker.check_empty_fields(variant))
        return issues

    @staticmethod
    def check_platform_limits(variant: CopyVariant) -> List[EditorialIssue]:
        issues: List[EditorialIssue] = []
        limits = PLATFORM_LIMITS.get(variant.platform, {})
        headline_limit = limits.get("headline", 200)
        text_limit = limits.get("primary_text", 5000)
        cta_limit = limits.get("cta", 50)

        if variant.headline and len(variant.headline) > headline_limit:
            issues.append(EditorialIssue(
                check_type="deterministic",
                severity="error",
                issue=f"Headline exceeds {headline_limit} characters (current: {len(variant.headline)})",
                field="headline",
                required_action=f"Reduce headline to under {headline_limit} characters.",
            ))
        if variant.primary_text and len(variant.primary_text) > text_limit:
            issues.append(EditorialIssue(
                check_type="deterministic",
                severity="error",
                issue=f"Primary text exceeds {text_limit} characters (current: {len(variant.primary_text)})",
                field="primary_text",
                required_action=f"Reduce primary text to under {text_limit} characters.",
            ))
        if variant.cta and len(variant.cta) > cta_limit:
            issues.append(EditorialIssue(
                check_type="deterministic",
                severity="error",
                issue=f"CTA exceeds {cta_limit} characters (current: {len(variant.cta)})",
                field="cta",
                required_action=f"Reduce CTA to under {cta_limit} characters.",
            ))
        return issues

    @staticmethod
    def check_required_fields(variant: CopyVariant) -> List[EditorialIssue]:
        issues: List[EditorialIssue] = []
        if not variant.headline:
            issues.append(EditorialIssue(check_type="deterministic", severity="error", issue="Headline is missing.", field="headline", required_action="Add a compelling headline."))
        if not variant.primary_text:
            issues.append(EditorialIssue(check_type="deterministic", severity="error", issue="Primary text is missing.", field="primary_text", required_action="Add primary body text."))
        if not variant.cta:
            issues.append(EditorialIssue(check_type="deterministic", severity="error", issue="CTA is missing.", field="cta", required_action="Add a clear call to action."))
        return issues

    @staticmethod
    def check_cta_presence(variant: CopyVariant, brief: CampaignBrief) -> List[EditorialIssue]:
        issues: List[EditorialIssue] = []
        if brief.cta and variant.cta:
            combined = (variant.headline + " " + variant.primary_text + " " + variant.cta).lower()
            if brief.cta.lower() not in combined:
                issues.append(EditorialIssue(
                    check_type="deterministic",
                    severity="warning",
                    issue=f"Campaign CTA '{brief.cta}' not clearly reflected in copy.",
                    field="cta",
                    required_action=f"Incorporate the campaign CTA: '{brief.cta}'.",
                ))
        return issues

    @staticmethod
    def check_duplicate_content(variant: CopyVariant) -> List[EditorialIssue]:
        issues: List[EditorialIssue] = []
        texts = [variant.headline, variant.primary_text, variant.subheadline or "", variant.cta]
        unique_texts = set(t.strip().lower() for t in texts if t.strip())
        if len(unique_texts) < len([t for t in texts if t.strip()]):
            issues.append(EditorialIssue(
                check_type="deterministic",
                severity="warning",
                issue="Duplicate content detected across copy fields.",
                field="primary_text",
                required_action="Ensure headline, body, and CTA are distinct.",
            ))
        return issues

    @staticmethod
    def check_readability(variant: CopyVariant) -> List[EditorialIssue]:
        issues: List[EditorialIssue] = []
        text = f"{variant.headline} {variant.primary_text}"
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_len > 30:
                issues.append(EditorialIssue(
                    check_type="deterministic",
                    severity="info",
                    issue=f"Average sentence length is {avg_len:.1f} words. Consider shorter sentences for readability.",
                    field="primary_text",
                    required_action="Break long sentences into shorter ones.",
                ))
        return issues

    @staticmethod
    def check_empty_fields(variant: CopyVariant) -> List[EditorialIssue]:
        issues: List[EditorialIssue] = []
        if not variant.headline or not variant.headline.strip():
            issues.append(EditorialIssue(check_type="deterministic", severity="error", issue="Headline is empty.", field="headline", required_action="Provide a headline."))
        if not variant.primary_text or not variant.primary_text.strip():
            issues.append(EditorialIssue(check_type="deterministic", severity="error", issue="Primary text is empty.", field="primary_text", required_action="Provide primary text."))
        if not variant.cta or not variant.cta.strip():
            issues.append(EditorialIssue(check_type="deterministic", severity="error", issue="CTA is empty.", field="cta", required_action="Provide a call to action."))
        return issues
