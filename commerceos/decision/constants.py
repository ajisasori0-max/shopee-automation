"""Decision Engine status and category enumerations."""

from enum import Enum


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class DecisionCategory(str, Enum):
    PRICING = "pricing"
    ADVERTISING = "advertising"
    INVENTORY = "inventory"
    FINANCE = "finance"
    OPERATIONS = "operations"


class DecisionSeverity(str, Enum):
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceSource(str, Enum):
    INSIGHT = "insight"
    KPI = "kpi"
    COMMERCE_STATE = "commerce_state"
    MONITORING_ALERT = "monitoring_alert"
    BUSINESS_RULE = "business_rule"


SEVERITY_RANK = {
    DecisionSeverity.INFO: 0,
    DecisionSeverity.NOTICE: 1,
    DecisionSeverity.WARNING: 2,
    DecisionSeverity.HIGH: 3,
    DecisionSeverity.CRITICAL: 4,
}


def severity_rank(severity) -> int:
    if isinstance(severity, DecisionSeverity):
        return SEVERITY_RANK[severity]
    return SEVERITY_RANK.get(DecisionSeverity(severity), 0)


def worst_severity(severities) -> DecisionSeverity:
    ranked = sorted(
        [s if isinstance(s, DecisionSeverity) else DecisionSeverity(s) for s in severities if s],
        key=severity_rank,
        reverse=True,
    )
    return ranked[0] if ranked else DecisionSeverity.INFO


STATUS_TRANSITIONS = {
    DecisionStatus.PROPOSED: {DecisionStatus.APPROVED, DecisionStatus.REJECTED, DecisionStatus.EXPIRED},
    DecisionStatus.APPROVED: {DecisionStatus.EXECUTED, DecisionStatus.EXPIRED},
    DecisionStatus.REJECTED: set(),
    DecisionStatus.EXECUTED: set(),
    DecisionStatus.EXPIRED: set(),
}


def can_transition(from_status: DecisionStatus, to_status: DecisionStatus) -> bool:
    return to_status in STATUS_TRANSITIONS.get(from_status, set())
