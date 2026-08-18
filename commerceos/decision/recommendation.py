"""Recommendation builder value object.

Rules produce plain dict recommendations. The engine converts them into Decision
records with evidence and estimated impact.
"""

from typing import Any, Dict, List, Optional


class Recommendation:
    def __init__(
        self,
        category: str,
        severity: str,
        title: str,
        description: str,
        rationale: str,
        recommended_action: str,
        expected_impact: Dict[str, Any],
        confidence: str,
        evidence: List[Dict[str, Any]],
    ):
        self.category = category
        self.severity = severity
        self.title = title
        self.description = description
        self.rationale = rationale
        self.recommended_action = recommended_action
        self.expected_impact = expected_impact
        self.confidence = confidence
        self.evidence = evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "recommended_action": self.recommended_action,
            "expected_impact": self.expected_impact,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }
