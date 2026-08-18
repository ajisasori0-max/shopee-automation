"""Comparison and context helpers."""

from typing import Any, Dict, List, Optional


def format_currency(value: Optional[float], currency: str = "IDR") -> str:
    if value is None:
        return f"N/A {currency}"
    return f"Rp {value:,.0f}"


def format_pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A%"
    return f"{value:+.1f}%"


def compare_metrics(current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
    """Build a side-by-side comparison of two metric dictionaries."""
    keys = set(current.keys()) | set(previous.keys())
    result = {}
    for key in sorted(keys):
        c = current.get(key)
        p = previous.get(key)
        delta = None
        delta_pct = None
        if c is not None and p is not None and p != 0:
            delta = float(c) - float(p)
            delta_pct = delta / float(p) * 100
        result[key] = {
            "current": c,
            "previous": p,
            "delta": delta,
            "delta_pct": delta_pct,
        }
    return result


def describe_change(delta_pct: Optional[float]) -> str:
    if delta_pct is None:
        return "changed"
    if abs(delta_pct) < 1:
        return "remained stable"
    if delta_pct >= 10:
        return "increased sharply"
    if delta_pct >= 1:
        return "increased"
    if delta_pct <= -10:
        return "decreased sharply"
    return "decreased"
