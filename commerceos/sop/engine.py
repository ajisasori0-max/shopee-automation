"""Operational SOP Engine — deterministic, auditable standard operating procedures.

WP3.4 introduces a rule-driven SOP execution layer that sits above the existing
Decision Engine. SOPs are explicit, versioned, enable/disable-able procedures
for recurring business situations. They are *not* uncontrolled LLM behavior:
LLMs may later explain or recommend, but the business logic is inspectable,
repeatable, and auditable.

"""

from commerceos.shared.value_objects.primitives import utc_now

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from commerceos.commerce.models import AdPerformance, Campaign, Expense, Inventory, Order, OrderItem, Payment, Product, Variant
from commerceos.config.settings import get_settings
from commerceos.decision.constants import DecisionCategory, DecisionConfidence, DecisionSeverity, EvidenceSource
from commerceos.decision.engine import DecisionEngine
from commerceos.decision.models import Decision, DecisionEvidence
from commerceos.decision.recommendation import Recommendation
from commerceos.events.bus import publish_event
from commerceos.events.constants import EventType
from commerceos.knowledge.organizational_memory import OrganizationalMemory
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.knowledge.writer import ObsidianWriter
from commerceos.sop.models import SOPDefinitionRecord, SOPExecutionRecord
from commerceos.sop.sqlalchemy_repositories import SQLAlchemySOPUnitOfWork

DEFAULT_SOP_VERSION = "1.0.0"


@dataclass
class SOPStep:
    """One ordered step inside a SOP.

    A step has a name, an optional condition that must be true for the step to
    apply, a list of required inputs, and a list of expected outputs. Conditions
    are deterministic business predicates (e.g. ``coverage_days < 7``). The SOP
    engine evaluates them against the context and records the result.
    """

    name: str
    description: str
    condition: Optional[str] = None
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    decision_point: bool = False
    approval_required: bool = False


@dataclass
class SOPDefinition:
    """A standard operating procedure definition.

    SOPs are identified by a stable code, carry an explicit version, and can be
    enabled or disabled. The trigger is a simple business event identifier that
    the SOP Engine matches when evaluating the system.
    """

    code: str
    name: str
    category: str
    trigger: str
    description: str
    version: str = DEFAULT_SOP_VERSION
    enabled: bool = True
    steps: List[SOPStep] = field(default_factory=list)
    severity: str = DecisionSeverity.WARNING.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "trigger": self.trigger,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "steps": [self._step_to_dict(s) for s in self.steps],
            "severity": self.severity,
        }

    @staticmethod
    def _step_to_dict(step: SOPStep) -> Dict[str, Any]:
        return {
            "name": step.name,
            "description": step.description,
            "condition": step.condition,
            "inputs": step.inputs,
            "outputs": step.outputs,
            "decision_point": step.decision_point,
            "approval_required": step.approval_required,
        }


@dataclass
class SOPExecution:
    """Result of running one SOP against a context.

    ``applies`` is True when the SOP trigger and all step conditions are satisfied.
    ``branches`` records which path was taken through conditional steps. The
    ``outputs`` dictionary is the deterministic recommendation that can be turned
    into a Decision record.
    """

    sop_code: str
    sop_name: str
    applies: bool
    trigger: str
    context: Dict[str, Any] = field(default_factory=dict)
    branches: List[str] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_id: str = ""
    executed_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sop_code": self.sop_code,
            "sop_name": self.sop_name,
            "applies": self.applies,
            "trigger": self.trigger,
            "context": self.context,
            "branches": self.branches,
            "outputs": self.outputs,
            "errors": self.errors,
            "execution_id": self.execution_id,
            "executed_at": self.executed_at.isoformat(),
        }


class SOPRunner(ABC):
    """Abstract executor for a single SOP definition.

    Given a SOP definition and a context, produces an SOPExecution. Concrete
    runners implement the business logic for a specific SOP code.
    """

    def __init__(self, sop: SOPDefinition):
        self.sop = sop

    @abstractmethod
    def run(self, session: Session, store_id: str, context: Dict[str, Any]) -> SOPExecution:
        raise NotImplementedError

    def _step_applies(self, step: SOPStep, context: Dict[str, Any]) -> bool:
        if not step.condition:
            return True
        try:
            return self._eval_condition(step.condition, context)
        except Exception:
            return False

    @staticmethod
    def _eval_condition(condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a simple comparison expression against the context.

        Only a small set of safe operations is allowed: ``< <= > >= == != in`` and
        attribute/dict access. This is intentionally limited to avoid arbitrary code
        execution.
        """
        condition = condition.strip()
        if "<" in condition:
            left, right = SOPRunner._split(condition, "<")
            return SOPRunner._resolve(left, context) < SOPRunner._resolve(right, context)
        if ">" in condition:
            left, right = SOPRunner._split(condition, ">")
            return SOPRunner._resolve(left, context) > SOPRunner._resolve(right, context)
        if "==" in condition:
            left, right = SOPRunner._split(condition, "==")
            return SOPRunner._resolve(left, context) == SOPRunner._resolve(right, context)
        if "!=" in condition:
            left, right = SOPRunner._split(condition, "!=")
            return SOPRunner._resolve(left, context) != SOPRunner._resolve(right, context)
        if " in " in condition:
            left, right = SOPRunner._split(condition, " in ")
            return SOPRunner._resolve(left, context) in SOPRunner._resolve(right, context)
        return bool(SOPRunner._resolve(condition, context))

    @staticmethod
    def _split(condition: str, operator: str) -> Tuple[str, str]:
        parts = condition.split(operator, 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid condition: {condition}")
        return parts[0].strip(), parts[1].strip()

    @staticmethod
    def _resolve(token: str, context: Dict[str, Any]) -> Any:
        token = token.strip()
        try:
            return float(token)
        except ValueError:
            pass
        if (token.startswith("'") and token.endswith("'")) or (token.startswith('"') and token.endswith('"')):
            return token[1:-1]
        if token.lower() == "true":
            return True
        if token.lower() == "false":
            return False
        value = context
        for part in token.split("."):
            if value is None:
                return None
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, None)
        return value

    def _new_execution(self, applies: bool, context: Dict[str, Any]) -> SOPExecution:
        return SOPExecution(
            sop_code=self.sop.code,
            sop_name=self.sop.name,
            applies=applies,
            trigger=self.sop.trigger,
            context=context,
            execution_id=f"sop-{self.sop.code}-{utc_now().strftime('%Y%m%d%H%M%S')}",
        )


# ---------------------------------------------------------------------------
# Built-in SOP definitions
# ---------------------------------------------------------------------------

LOW_STOCK_SOP = SOPDefinition(
    code="LOW_STOCK",
    name="Low Stock Replenishment",
    category=DecisionCategory.INVENTORY.value,
    trigger="inventory_low_coverage",
    description="Evaluate low stock SKUs and produce a replenishment recommendation.",
    severity=DecisionSeverity.WARNING.value,
    steps=[
        SOPStep(
            name="Identify low coverage SKUs",
            description="List SKUs with coverage below the safety threshold.",
            inputs=["inventory_summary"],
            outputs=["low_coverage_skus"],
        ),
        SOPStep(
            name="Compute recent velocity",
            description="Use recent order velocity to estimate daily demand.",
            condition="coverage_days < 7",
            inputs=["order_velocity", "inventory_summary"],
            outputs=["daily_velocity"],
        ),
        SOPStep(
            name="Assess supplier lead time",
            description="Combine lead time with demand to estimate days until replenishment arrives.",
            condition="coverage_days < 7",
            inputs=["lead_time_days", "daily_velocity"],
            outputs=["lead_time_demand"],
        ),
        SOPStep(
            name="Recommend purchase order",
            description="Recommend a PO quantity that covers the gap until stock is safe.",
            condition="coverage_days < 7",
            inputs=["daily_velocity", "lead_time_days", "coverage_days", "stock_available"],
            outputs=["recommended_po_quantity"],
            decision_point=True,
            approval_required=True,
        ),
    ],
)

ROAS_COLLAPSE_SOP = SOPDefinition(
    code="ROAS_COLLAPSE",
    name="ROAS Collapse Diagnosis",
    category=DecisionCategory.ADVERTISING.value,
    trigger="roas_collapse",
    description="Diagnose a sudden ROAS collapse and recommend a safe action.",
    severity=DecisionSeverity.HIGH.value,
    steps=[
        SOPStep(
            name="Capture campaign context",
            description="Identify the campaign, recent spend, and current ROAS.",
            inputs=["campaign_summary", "roas_current", "roas_baseline"],
            outputs=["campaign_id", "spend_current", "roas_current"],
        ),
        SOPStep(
            name="Check traffic and conversion",
            description="Determine whether the issue is traffic (CTR) or conversion (ROAS per click).",
            condition="roas_current < roas_baseline",
            inputs=["ctr", "clicks", "conversions", "spend"],
            outputs=["traffic_diagnosis", "conversion_diagnosis"],
        ),
        SOPStep(
            name="SKU/product performance",
            description="Compare SKU-level ad revenue to identify whether a single SKU is dragging ROAS.",
            condition="roas_current < 2.0",
            inputs=["ad_performance_by_sku"],
            outputs=["worst_performing_skus"],
        ),
        SOPStep(
            name="Historical comparison",
            description="Find similar past ROAS collapse events and what was done.",
            condition="roas_current < 2.0",
            inputs=["knowledge_history"],
            outputs=["comparable_incidents"],
        ),
        SOPStep(
            name="Recommend action",
            description="Pause or reduce budget for the underperforming campaign or SKU.",
            condition="roas_current < 2.0",
            inputs=["worst_performing_skus", "campaign_id", "spend_current"],
            outputs=["recommended_action"],
            decision_point=True,
            approval_required=True,
        ),
    ],
)

REVENUE_DROP_SOP = SOPDefinition(
    code="REVENUE_DROP",
    name="Revenue Drop Diagnosis",
    category=DecisionCategory.OPERATIONS.value,
    trigger="revenue_drop",
    description="Diagnose a revenue drop and identify the most likely causes.",
    severity=DecisionSeverity.HIGH.value,
    steps=[
        SOPStep(
            name="Compare revenue and orders",
            description="Quantify the drop in revenue and orders.",
            inputs=["revenue_current", "revenue_baseline", "orders_current", "orders_baseline"],
            outputs=["revenue_delta_pct", "orders_delta_pct"],
        ),
        SOPStep(
            name="Evaluate traffic and conversion",
            description="Determine if the drop is from fewer visitors or lower conversion.",
            condition="revenue_delta_pct < -0.10",
            inputs=["traffic_current", "traffic_baseline", "conversion_current", "conversion_baseline"],
            outputs=["traffic_delta_pct", "conversion_delta_pct"],
        ),
        SOPStep(
            name="Check advertising",
            description="Check whether a spend or ROAS change is correlated.",
            condition="revenue_delta_pct < -0.10",
            inputs=["ad_spend_current", "ad_spend_baseline", "roas_current", "roas_baseline"],
            outputs=["ad_spend_delta_pct", "roas_delta_pct"],
        ),
        SOPStep(
            name="Check product availability",
            description="Check if out-of-stock SKUs are linked to the revenue drop.",
            condition="revenue_delta_pct < -0.10",
            inputs=["zero_stock_skus"],
            outputs=["stock_related_drop"],
        ),
        SOPStep(
            name="Check price changes",
            description="Identify recent price changes that may have changed demand elasticity.",
            condition="revenue_delta_pct < -0.10",
            inputs=["price_changes"],
            outputs=["price_change_impact"],
        ),
        SOPStep(
            name="Historical comparison",
            description="Find similar past revenue drops and what was done.",
            condition="revenue_delta_pct < -0.10",
            inputs=["knowledge_history"],
            outputs=["comparable_incidents"],
        ),
        SOPStep(
            name="Recommend action",
            description="Suggest a targeted action based on the diagnosed cause.",
            condition="revenue_delta_pct < -0.10",
            inputs=["traffic_delta_pct", "conversion_delta_pct", "stock_related_drop", "price_change_impact"],
            outputs=["recommended_action"],
            decision_point=True,
            approval_required=True,
        ),
    ],
)

CASH_PRESSURE_SOP = SOPDefinition(
    code="CASH_PRESSURE",
    name="Cash Pressure Assessment",
    category=DecisionCategory.FINANCE.value,
    trigger="cash_pressure",
    description="Assess projected cash position and recommend a financing or spending action.",
    severity=DecisionSeverity.HIGH.value,
    steps=[
        SOPStep(
            name="Cash position",
            description="Current cash balance and recent cash flow.",
            inputs=["cash_balance", "recent_net_cash_flow"],
            outputs=["cash_position"],
        ),
        SOPStep(
            name="Upcoming bills",
            description="Known upcoming bills and payables.",
            condition="cash_balance < 50000000",
            inputs=["upcoming_bills"],
            outputs=["bills_total"],
        ),
        SOPStep(
            name="Inventory requirements",
            description="Cash required to cover recommended reorders.",
            condition="cash_balance < 50000000",
            inputs=["recommended_po_total"],
            outputs=["inventory_cash_required"],
        ),
        SOPStep(
            name="Expected revenue and ad spend",
            description="Forecast inflows and outflows from operations.",
            condition="cash_balance < 50000000",
            inputs=["forecast_revenue", "forecast_ad_spend"],
            outputs=["operational_cash_delta"],
        ),
        SOPStep(
            name="Projected cash requirement",
            description="Project cash balance after obligations and recommend action.",
            condition="cash_balance < 50000000",
            inputs=["cash_balance", "bills_total", "inventory_cash_required", "operational_cash_delta"],
            outputs=["projected_cash_balance", "recommended_action"],
            decision_point=True,
            approval_required=True,
        ),
    ],
)

DEFAULT_SOP_DEFINITIONS = [LOW_STOCK_SOP, ROAS_COLLAPSE_SOP, REVENUE_DROP_SOP, CASH_PRESSURE_SOP]


# ---------------------------------------------------------------------------
# Data collection helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _days_ago(days: int) -> datetime:
    return utc_now() - timedelta(days=days)


def _inventory_context(session: Session, store_id: str) -> Dict[str, Any]:
    """Collect inventory data for the LOW_STOCK SOP."""
    rows = (
        session.query(
            Inventory.quantity_available,
            Inventory.quantity_reserved,
            Variant.sku,
            Variant.selling_price,
            Product.name,
            Variant.id,
        )
        .join(Variant, Inventory.variant_id == Variant.id)
        .join(Product, Variant.product_id == Product.id)
        .filter(Inventory.store_id == store_id)
        .all()
    )

    inventory_items = []
    for row in rows:
        available = row.quantity_available or 0
        sku = row.sku or f"variant-{row.id[:8]}"
        inventory_items.append({
            "sku": sku,
            "product_name": row.name or "Unknown",
            "available": available,
            "reserved": row.quantity_reserved or 0,
            "selling_price": _safe_float(row.selling_price),
        })

    since = _days_ago(14)
    order_items = (
        session.query(
            OrderItem.sku,
            func.sum(OrderItem.quantity).label("qty"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.store_id == store_id,
            Order.ordered_at >= since,
            Order.status.notin_(["cancelled"]),
        )
        .group_by(OrderItem.sku)
        .all()
    )
    velocity_by_sku = {item.sku: int(item.qty or 0) / 14.0 for item in order_items if item.sku}

    default_lead_time = 7
    for item in inventory_items:
        sku = item["sku"]
        velocity = velocity_by_sku.get(sku, 0.0)
        item["daily_velocity"] = velocity
        item["lead_time_days"] = default_lead_time
        item["coverage_days"] = (item["available"] / velocity) if velocity > 0 else 999.0

    return {
        "inventory_items": inventory_items,
        "velocity_by_sku": velocity_by_sku,
        "lead_time_days_default": default_lead_time,
    }


def _ad_context(session: Session, store_id: str, days: int = 7) -> Dict[str, Any]:
    """Collect ad performance context for the ROAS_COLLAPSE SOP."""
    since = _days_ago(days)
    perf = (
        session.query(
            AdPerformance.campaign_id,
            func.sum(AdPerformance.spend).label("total_spend"),
            func.sum(AdPerformance.revenue).label("total_revenue"),
            func.sum(AdPerformance.clicks).label("total_clicks"),
            func.sum(AdPerformance.impressions).label("total_impressions"),
            func.sum(AdPerformance.conversions).label("total_conversions"),
        )
        .filter(
            AdPerformance.store_id == store_id,
            AdPerformance.date >= since,
        )
        .group_by(AdPerformance.campaign_id)
        .all()
    )

    campaign_rows = (
        session.query(Campaign.id, Campaign.marketplace_campaign_id, Campaign.name)
        .filter(Campaign.store_id == store_id)
        .all()
    )
    campaign_names = {r.id: r.name for r in campaign_rows}
    campaign_ext = {r.id: r.marketplace_campaign_id for r in campaign_rows}

    by_campaign = []
    for row in perf:
        spend = _safe_float(row.total_spend) or 0.0
        revenue = _safe_float(row.total_revenue) or 0.0
        roas = (revenue / spend) if spend else 0.0
        clicks = int(row.total_clicks or 0)
        impressions = int(row.total_impressions or 0)
        ctr = (clicks / impressions * 100) if impressions else 0.0
        by_campaign.append({
            "campaign_id": row.campaign_id,
            "campaign_name": campaign_names.get(row.campaign_id, "Unknown"),
            "marketplace_campaign_id": campaign_ext.get(row.campaign_id, ""),
            "spend": spend,
            "revenue": revenue,
            "roas": roas,
            "clicks": clicks,
            "impressions": impressions,
            "ctr": ctr,
            "conversions": int(row.total_conversions or 0),
        })

    total_spend = sum(r["spend"] for r in by_campaign)
    total_revenue = sum(r["revenue"] for r in by_campaign)
    total_clicks = sum(r["clicks"] for r in by_campaign)
    total_impressions = sum(r["impressions"] for r in by_campaign)
    overall_roas = (total_revenue / total_spend) if total_spend else 0.0
    overall_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0.0

    return {
        "by_campaign": by_campaign,
        "total_spend": total_spend,
        "total_revenue": total_revenue,
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "total_conversions": sum(r["conversions"] for r in by_campaign),
        "overall_roas": overall_roas,
        "overall_ctr": overall_ctr,
    }


def _order_aggregates(session: Session, store_id: str, start: datetime, end: datetime) -> Dict[str, Any]:
    row = (
        session.query(
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
        )
        .filter(
            Order.store_id == store_id,
            Order.ordered_at >= start,
            Order.ordered_at < end,
            Order.status.notin_(["cancelled"]),
        )
        .first()
    )
    orders = int(row.order_count or 0) if row else 0
    revenue = _safe_float(row.revenue) or 0.0 if row else 0.0
    return {"orders": orders, "revenue": revenue, "aov": (revenue / orders) if orders else 0.0}


def _ad_window(session: Session, store_id: str, start: datetime, end: datetime) -> Dict[str, Any]:
    row = (
        session.query(
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.revenue).label("revenue"),
            func.sum(AdPerformance.impressions).label("impressions"),
            func.sum(AdPerformance.conversions).label("conversions"),
        )
        .filter(
            AdPerformance.store_id == store_id,
            AdPerformance.date >= start,
            AdPerformance.date < end,
        )
        .first()
    )
    spend = _safe_float(row.spend) or 0.0 if row else 0.0
    revenue = _safe_float(row.revenue) or 0.0 if row else 0.0
    return {
        "spend": spend,
        "revenue": revenue,
        "impressions": int(row.impressions or 0) if row else 0,
        "conversions": int(row.conversions or 0) if row else 0,
        "roas": (revenue / spend) if spend else 0.0,
    }


def _revenue_context(session: Session, store_id: str, days: int = 7) -> Dict[str, Any]:
    """Collect revenue and order context for the REVENUE_DROP SOP."""
    end = utc_now()
    start = end - timedelta(days=days)
    baseline_start = start - timedelta(days=days)

    current = _order_aggregates(session, store_id, start, end)
    baseline = _order_aggregates(session, store_id, baseline_start, start)

    current_ad = _ad_window(session, store_id, start, end)
    baseline_ad = _ad_window(session, store_id, baseline_start, start)

    zero_stock = [
        item["sku"] for item in _inventory_context(session, store_id)["inventory_items"] if item["available"] <= 0
    ]

    price_changes = "price history not available"

    def _pct_delta(current_val: float, baseline_val: float) -> Optional[float]:
        if baseline_val == 0 or baseline_val is None:
            return None
        return (current_val - baseline_val) / baseline_val

    return {
        "revenue_current": current["revenue"],
        "revenue_baseline": baseline["revenue"],
        "revenue_delta_pct": _pct_delta(current["revenue"], baseline["revenue"]),
        "orders_current": current["orders"],
        "orders_baseline": baseline["orders"],
        "orders_delta_pct": _pct_delta(current["orders"], baseline["orders"]),
        "aov_current": current["aov"],
        "aov_baseline": baseline["aov"],
        "traffic_current": current_ad["impressions"],
        "traffic_baseline": baseline_ad["impressions"],
        "traffic_delta_pct": _pct_delta(current_ad["impressions"], baseline_ad["impressions"]),
        "conversion_current": current_ad["conversions"],
        "conversion_baseline": baseline_ad["conversions"],
        "conversion_delta_pct": _pct_delta(current_ad["conversions"], baseline_ad["conversions"]),
        "ad_spend_current": current_ad["spend"],
        "ad_spend_baseline": baseline_ad["spend"],
        "ad_sprint_delta_pct": _pct_delta(current_ad["spend"], baseline_ad["spend"]),
        "ad_spend_delta_pct": _pct_delta(current_ad["spend"], baseline_ad["spend"]),
        "roas_current": current_ad["roas"],
        "roas_baseline": baseline_ad["roas"],
        "roas_delta_pct": _pct_delta(current_ad["roas"], baseline_ad["roas"]),
        "zero_stock_skus": zero_stock,
        "price_changes": price_changes,
    }


def _cash_context(session: Session, store_id: str, days: int = 14) -> Dict[str, Any]:
    """Collect cash-related context for the CASH_PRESSURE SOP.

    Cash balance is not directly available as a first-class entity. We derive what
    we can from payments and expenses, and honestly report what is missing.
    """
    since = _days_ago(days)
    payment_row = (
        session.query(
            func.sum(Payment.net_amount).label("net_inflow"),
        )
        .filter(
            Payment.store_id == store_id,
            Payment.paid_at >= since,
        )
        .first()
    )
    net_inflow = _safe_float(payment_row.net_inflow) or 0.0 if payment_row else 0.0
    daily_net_inflow = net_inflow / days

    expense_row = (
        session.query(
            func.sum(Expense.amount).label("expenses"),
        )
        .filter(
            Expense.store_id == store_id,
            Expense.incurred_at >= since,
        )
        .first()
    )
    expenses = _safe_float(expense_row.expenses) if expense_row and expense_row.expenses is not None else None

    cash_balance = None
    upcoming_bills = None
    if expenses is not None:
        upcoming_bills = (expenses / days) * 30

    return {
        "cash_balance": cash_balance,
        "cash_balance_available": False,
        "recent_net_inflow": net_inflow,
        "daily_net_inflow": daily_net_inflow,
        "recent_expenses": expenses,
        "expenses_available": expenses is not None,
        "upcoming_bills": upcoming_bills,
        "recommended_po_total": None,
    }


# ---------------------------------------------------------------------------
# Concrete SOP runners
# ---------------------------------------------------------------------------

class LowStockRunner(SOPRunner):
    """Execute the LOW_STOCK SOP."""

    COVERAGE_THRESHOLD = 7.0
    SAFETY_STOCK_DAYS = 7.0

    def run(self, session: Session, store_id: str, context: Dict[str, Any]) -> SOPExecution:
        items = context.get("inventory_items", [])
        low_items = [item for item in items if item.get("coverage_days", 999.0) < self.COVERAGE_THRESHOLD]

        if not low_items:
            exec_result = self._new_execution(False, context)
            exec_result.branches.append("No SKUs below coverage threshold")
            return exec_result

        low_items.sort(key=lambda x: x.get("coverage_days", 999.0))

        recommendations = []
        for item in low_items[:10]:
            velocity = item.get("daily_velocity", 0.0)
            lead_time = item.get("lead_time_days", 7)
            available = item.get("available", 0)
            target_stock = (lead_time + self.SAFETY_STOCK_DAYS) * velocity
            qty = max(0, int(target_stock - available))
            recommendations.append({
                "sku": item["sku"],
                "product_name": item["product_name"],
                "available": available,
                "daily_velocity": round(velocity, 2),
                "coverage_days": round(item.get("coverage_days", 0.0), 1),
                "lead_time_days": lead_time,
                "recommended_po_quantity": qty,
                "estimated_po_value": round(qty * (item.get("selling_price") or 0), 2),
            })

        total_po_value = sum(r["estimated_po_value"] for r in recommendations)
        total_po_quantity = sum(r["recommended_po_quantity"] for r in recommendations)

        exec_result = self._new_execution(True, context)
        exec_result.branches.append(f"{len(low_items)} SKU(s) below {self.COVERAGE_THRESHOLD}-day coverage")
        exec_result.outputs = {
            "low_coverage_skus": [r["sku"] for r in recommendations],
            "recommendations": recommendations,
            "total_recommended_po_quantity": total_po_quantity,
            "total_estimated_po_value": total_po_value,
            "recommended_action": "Approve purchase orders for low-coverage SKUs",
            "missing_inputs": [],
        }
        return exec_result


class ROASCollapseRunner(SOPRunner):
    """Execute the ROAS_COLLAPSE SOP."""

    ROAS_CRITICAL = 1.0
    ROAS_LOW = 2.0

    def run(self, session: Session, store_id: str, context: Dict[str, Any]) -> SOPExecution:
        overall_roas = context.get("overall_roas")
        total_spend = context.get("total_spend", 0.0)
        if overall_roas is None:
            exec_result = self._new_execution(False, context)
            exec_result.errors.append("No ROAS data available")
            return exec_result

        if overall_roas >= self.ROAS_LOW or total_spend == 0:
            exec_result = self._new_execution(False, context)
            if total_spend == 0:
                exec_result.branches.append("No ad spend; ROAS collapse SOP does not apply")
            else:
                exec_result.branches.append(f"Overall ROAS {overall_roas:.2f} is above {self.ROAS_LOW}")
            return exec_result

        by_campaign = context.get("by_campaign", [])
        worst = None
        if by_campaign:
            worst = min(by_campaign, key=lambda x: x.get("roas", 999.0))

        diagnosis = []
        if worst:
            if worst.get("ctr", 0.0) < 0.5:
                diagnosis.append("Traffic is low (CTR < 0.5%)")
            if worst.get("conversions", 0) == 0 or worst.get("roas", 0.0) < 1.0:
                diagnosis.append("Conversion is poor; clicks are not returning revenue")

        comparable = context.get("knowledge_history", [])

        exec_result = self._new_execution(True, context)
        exec_result.branches.append(f"Overall ROAS {overall_roas:.2f} below {self.ROAS_LOW}")
        if worst:
            exec_result.branches.append(
                f"Worst campaign: {worst['campaign_name']} ROAS {worst['roas']:.2f}"
            )

        action = "Reduce campaign budget by 20% until ROAS recovers"
        if overall_roas < self.ROAS_CRITICAL:
            action = "Pause the worst-performing campaign immediately"

        exec_result.outputs = {
            "overall_roas": overall_roas,
            "worst_campaign": worst,
            "diagnosis": diagnosis,
            "comparable_incidents": comparable[:3] if comparable else [],
            "recommended_action": action,
            "missing_inputs": [],
        }
        return exec_result


class RevenueDropRunner(SOPRunner):
    """Execute the REVENUE_DROP SOP."""

    REVENUE_DROP_THRESHOLD = -0.10

    def run(self, session: Session, store_id: str, context: Dict[str, Any]) -> SOPExecution:
        revenue_delta_pct = context.get("revenue_delta_pct")
        if revenue_delta_pct is None:
            exec_result = self._new_execution(False, context)
            exec_result.errors.append("Revenue delta unavailable")
            return exec_result

        if revenue_delta_pct >= self.REVENUE_DROP_THRESHOLD:
            exec_result = self._new_execution(False, context)
            exec_result.branches.append(
                f"Revenue delta {revenue_delta_pct*100:.1f}% is within threshold"
            )
            return exec_result

        causes = []
        traffic_delta = context.get("traffic_delta_pct")
        conversion_delta = context.get("conversion_delta_pct")
        if traffic_delta is not None and traffic_delta < -0.10:
            causes.append("Traffic fell significantly")
        if conversion_delta is not None and conversion_delta < -0.10:
            causes.append("Conversion fell significantly")
        if context.get("ad_spend_delta_pct", 0.0) < -0.20:
            causes.append("Ad spend reduction likely reduced traffic")
        if context.get("zero_stock_skus"):
            causes.append(f"{len(context['zero_stock_skus'])} SKU(s) out of stock")
        if context.get("price_changes") == "price history not available":
            causes.append("Price change history unavailable")

        def _pct_delta(current_val: float, baseline_val: float) -> Optional[float]:
            if baseline_val == 0 or baseline_val is None:
                return None
            return (current_val - baseline_val) / baseline_val

        exec_result = self._new_execution(True, context)
        exec_result.branches.append(f"Revenue dropped {revenue_delta_pct*100:.1f}%")
        exec_result.outputs = {
            "revenue_delta_pct": revenue_delta_pct,
            "orders_delta_pct": context.get("orders_delta_pct"),
            "aov_delta_pct": _pct_delta(context.get("aov_current", 0), context.get("aov_baseline", 0)),
            "traffic_delta_pct": traffic_delta,
            "conversion_delta_pct": conversion_delta,
            "ad_spend_delta_pct": context.get("ad_spend_delta_pct"),
            "roas_delta_pct": context.get("roas_delta_pct"),
            "zero_stock_skus": context.get("zero_stock_skus", []),
            "causes": causes,
            "comparable_incidents": context.get("knowledge_history", [])[:3],
            "recommended_action": "Diagnose root cause and run targeted experiment to recover revenue",
            "missing_inputs": [
                m for m in [
                    "traffic" if traffic_delta is None else None,
                    "conversion" if conversion_delta is None else None,
                    "price history" if context.get("price_changes") == "price history not available" else None,
                ] if m
            ],
        }
        return exec_result


class CashPressureRunner(SOPRunner):
    """Execute the CASH_PRESSURE SOP."""

    CASH_LOW_THRESHOLD = 50_000_000.0

    def run(self, session: Session, store_id: str, context: Dict[str, Any]) -> SOPExecution:
        cash_balance = context.get("cash_balance")
        if cash_balance is None:
            exec_result = self._new_execution(False, context)
            exec_result.branches.append("Cash balance not available; cannot assess cash pressure")
            exec_result.outputs = {
                "cash_balance": None,
                "recommended_action": "Connect cash balance data to enable cash pressure SOP",
                "missing_inputs": ["cash_balance"],
            }
            return exec_result

        if cash_balance >= self.CASH_LOW_THRESHOLD:
            exec_result = self._new_execution(False, context)
            exec_result.branches.append(f"Cash balance {cash_balance:,.0f} above threshold")
            return exec_result

        bills = context.get("upcoming_bills") or 0.0
        inventory_required = context.get("recommended_po_total") or 0.0
        operational_delta = context.get("daily_net_inflow", 0.0) * 30
        projected = cash_balance - bills - inventory_required + operational_delta

        exec_result = self._new_execution(True, context)
        exec_result.branches.append(f"Cash balance {cash_balance:,.0f} below threshold")
        exec_result.outputs = {
            "cash_balance": cash_balance,
            "upcoming_bills": bills,
            "inventory_cash_required": inventory_required,
            "operational_cash_delta_30d": operational_delta,
            "projected_cash_balance": projected,
            "recommended_action": "Defer discretionary spend and secure short-term cash buffer" if projected < 0 else "Monitor cash weekly",
            "missing_inputs": [] if context.get("expenses_available") else ["expenses"],
        }
        return exec_result


# ---------------------------------------------------------------------------
# SOP Engine
# ---------------------------------------------------------------------------

class SOPEngine:
    """Evaluate all enabled SOPs for a store and produce recommendations.

    The engine is stateless aside from its configured SOP definitions. It gathers
    context once per category and runs each runner. Results are turned into
    Recommendation objects suitable for the Decision Engine, and optionally
    published as events.
    """

    def __init__(
        self,
        sops: Optional[List[SOPDefinition]] = None,
        runners: Optional[Dict[str, type]] = None,
    ):
        self.sops = {s.code: s for s in (sops or DEFAULT_SOP_DEFINITIONS)}
        self.runners = runners or {
            "LOW_STOCK": LowStockRunner,
            "ROAS_COLLAPSE": ROASCollapseRunner,
            "REVENUE_DROP": RevenueDropRunner,
            "CASH_PRESSURE": CashPressureRunner,
        }

    def refresh(
        self,
        session: Session,
        store_id: str,
        publish_events: bool = True,
        knowledge_uow=None,
    ) -> Dict[str, Any]:
        """Run all enabled SOPs and return recommendations + executions."""
        contexts = self._gather_contexts(session, store_id, knowledge_uow)
        executions: List[SOPExecution] = []
        recommendations: List[Recommendation] = []

        for code, sop in self.sops.items():
            if not sop.enabled:
                continue
            runner_cls = self.runners.get(code)
            if runner_cls is None:
                continue
            context = contexts.get(code, {})
            runner = runner_cls(sop)
            execution = runner.run(session, store_id, context)
            executions.append(execution)
            if execution.applies:
                rec = self._execution_to_recommendation(sop, execution)
                if rec:
                    recommendations.append(rec)
                if publish_events:
                    self._publish_event(session, EventType.INSIGHT_GENERATED, execution)

        return {
            "store_id": store_id,
            "sop_count": len(self.sops),
            "executed": len(executions),
            "applicable": len([e for e in executions if e.applies]),
            "recommendations": [r.to_dict() for r in recommendations],
            "executions": [e.to_dict() for e in executions],
        }

    def _gather_contexts(
        self,
        session: Session,
        store_id: str,
        knowledge_uow=None,
    ) -> Dict[str, Dict[str, Any]]:
        """Gather the raw inputs for each SOP."""
        inventory_ctx = _inventory_context(session, store_id)
        ad_ctx = _ad_context(session, store_id)
        revenue_ctx = _revenue_context(session, store_id)
        cash_ctx = _cash_context(session, store_id)

        low_stock_runner = LowStockRunner(LOW_STOCK_SOP)
        low_exec = low_stock_runner.run(session, store_id, inventory_ctx)
        if low_exec.applies:
            cash_ctx["recommended_po_total"] = low_exec.outputs.get("total_estimated_po_value", 0.0)

        knowledge_history = self._recent_knowledge_history(session, store_id, knowledge_uow)
        ad_ctx["knowledge_history"] = knowledge_history
        revenue_ctx["knowledge_history"] = knowledge_history

        return {
            "LOW_STOCK": inventory_ctx,
            "ROAS_COLLAPSE": ad_ctx,
            "REVENUE_DROP": revenue_ctx,
            "CASH_PRESSURE": cash_ctx,
        }

    def _recent_knowledge_history(
        self,
        session: Session,
        store_id: str,
        knowledge_uow=None,
    ) -> List[Dict[str, Any]]:
        """Return a small list of recent relevant lessons from the knowledge layer."""
        if knowledge_uow is None:
            return []
        try:
            repo = knowledge_uow.notes()
            notes = repo.list(tags=["lesson"], limit=5)
            return [
                {
                    "note_id": n.note_id,
                    "title": n.title,
                    "note_date": n.note_date.isoformat() if n.note_date else None,
                }
                for n in notes
            ]
        except Exception:
            return []

    def _execution_to_recommendation(
        self,
        sop: SOPDefinition,
        execution: SOPExecution,
    ) -> Optional[Recommendation]:
        outputs = execution.outputs
        action = outputs.get("recommended_action", "Review SOP output")
        title = f"[{sop.code}] {sop.name}"
        description = self._build_description(sop, execution)
        rationale = (
            f"SOP {sop.code} v{sop.version} triggered. Branches: "
            f"{', '.join(execution.branches)}."
        )
        evidence = [
            {
                "source_type": EvidenceSource.BUSINESS_RULE.value,
                "source_id": execution.execution_id,
                "description": f"SOP execution: {execution.sop_code}",
            }
        ]
        expected_impact = {
            "expected_revenue_change": 0.0,
            "expected_profit_change": 0.0,
            "expected_cash_change": 0.0,
            "sop_outputs": outputs,
        }
        return Recommendation(
            category=sop.category,
            severity=sop.severity,
            title=title,
            description=description,
            rationale=rationale,
            recommended_action=action,
            expected_impact=expected_impact,
            confidence=DecisionConfidence.MEDIUM.value,
            evidence=evidence,
        )

    @staticmethod
    def _build_description(sop: SOPDefinition, execution: SOPExecution) -> str:
        outputs = execution.outputs
        parts = [f"SOP {sop.name} applies."]
        if "low_coverage_skus" in outputs:
            parts.append(f"SKUs: {', '.join(outputs['low_coverage_skus'][:5])}.")
        if "overall_roas" in outputs:
            parts.append(f"Overall ROAS: {outputs['overall_roas']:.2f}.")
        if "revenue_delta_pct" in outputs and outputs["revenue_delta_pct"] is not None:
            parts.append(f"Revenue delta: {outputs['revenue_delta_pct']*100:.1f}%.")
        if "causes" in outputs:
            parts.append(f"Causes: {', '.join(outputs['causes'])}.")
        if "cash_balance" in outputs:
            if outputs["cash_balance"] is None:
                parts.append("Cash balance unavailable.")
            else:
                parts.append(f"Cash balance: {outputs['cash_balance']:,.0f}.")
        if outputs.get("missing_inputs"):
            parts.append(f"Missing inputs: {', '.join(outputs['missing_inputs'])}.")
        return " ".join(parts)

    def _publish_event(self, session: Session, event_type: str, execution: SOPExecution) -> None:
        try:
            publish_event(
                session,
                event_type=event_type,
                aggregate_type="sop_execution",
                aggregate_id=execution.execution_id,
                payload={
                    "sop_code": execution.sop_code,
                    "applies": execution.applies,
                    "outputs": execution.outputs,
                },
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Knowledge recording
# ---------------------------------------------------------------------------

def record_sop_run_to_knowledge(
    session: Session,
    result: Dict[str, Any],
    vault_dir: Optional[str] = None,
) -> Dict[str, str]:
    """Write a reference note summarizing the SOP run."""
    settings = get_settings()

    vault = Path(vault_dir or settings.obsidian_vault_path)
    knowledge_uow = SQLAlchemyKnowledgeUnitOfWork(session)
    org_memory = OrganizationalMemory(repository=knowledge_uow.notes(), vault_dir=vault)

    lines = [
        "## SOP Run Summary",
        "",
        f"- Store: {result.get('store_id')}",
        f"- SOPs evaluated: {result.get('sop_count')}",
        f"- Applicable: {result.get('applicable')}",
        "",
        "## Applicable SOPs",
        "",
    ]
    for execution in result.get("executions", []):
        if not execution.get("applies"):
            continue
        lines.append(f"### {execution['sop_code']}")
        lines.append(f"- Branches: {', '.join(execution.get('branches', []))}")
        outputs = execution.get("outputs", {})
        action = outputs.get("recommended_action", "—")
        lines.append(f"- Recommended action: {action}")
        if outputs.get("missing_inputs"):
            lines.append(f"- Missing inputs: {', '.join(outputs['missing_inputs'])}")
        lines.append("")

    note = org_memory.create_lesson(
        title=f"SOP Run — {result.get('store_id')} ({utc_now().date().isoformat()})",
        text="\n".join(lines),
        related_note_ids=[],
        project="CommerceOS",
    )
    return note


# ---------------------------------------------------------------------------
# CLI / script entry point
# ---------------------------------------------------------------------------

def run_sop_engine(
    session: Session,
    store_id: str = "store-ppm-001",
    persist_decisions: bool = True,
    publish_events: bool = True,
    record_knowledge: bool = True,
    record_executions: bool = True,
) -> Dict[str, Any]:
    """High-level entry point used by operational scripts and tests.

    Persists SOP decisions through the canonical DecisionEngine to avoid duplicate
    recommendations and keep metadata consistent. SOP executions themselves are
    recorded to the sop_executions table for auditability.
    """
    engine = SOPEngine()
    knowledge_uow = SQLAlchemyKnowledgeUnitOfWork(session)
    sop_uow = SQLAlchemySOPUnitOfWork(session)

    result = engine.refresh(session, store_id, publish_events=publish_events, knowledge_uow=knowledge_uow)
    result["run_id"] = f"sop-run-{utc_now().strftime('%Y%m%d-%H%M%S')}"

    # Record each SOP execution for auditability.
    if record_executions:
        for execution in result.get("executions", []):
            try:
                record = SOPExecutionRecord(
                    sop_code=execution["sop_code"],
                    store_id=store_id,
                    execution_id=execution["execution_id"],
                    applies=execution["applies"],
                    branches=execution.get("branches", []),
                    outputs=execution.get("outputs", {}),
                    errors=execution.get("errors", []),
                    executed_at=utc_now(),
                    source_run_id=result["run_id"],
                )
                sop_uow.executions().save(record)
                sop_uow.commit()
            except Exception:
                sop_uow.rollback()

    # Persist decisions through the canonical DecisionEngine to avoid duplicates.
    if persist_decisions and result["recommendations"]:
        decision_engine = DecisionEngine(session)
        new_decisions = decision_engine.refresh_sop_recommendations(store_id, result)
        result["decision_ids"] = [d.id for d in new_decisions]

    if record_knowledge:
        try:
            record_sop_run_to_knowledge(session, result)
        except Exception:
            pass
    return result


if __name__ == "__main__":
    import sys

    from commerceos.platform.database.connection import get_session

    settings = get_settings()
    session = get_session(settings.database_url)
    try:
        result = run_sop_engine(session)
        print(f"SOP run complete: {result['applicable']}/{result['sop_count']} applicable")
        for rec in result["recommendations"]:
            print(f"- {rec['title']}: {rec['recommended_action']}")
    finally:
        session.close()
