"""Score interpretation helpers (plan module: analysis/scoring.py)."""


def score_band(score) -> dict:
    """Map a 0-100 score to a display band with color and label."""
    try:
        s = int(score)
    except (TypeError, ValueError):
        return {"label": "N/A", "color": "#9E9E9E", "emoji": "❔"}

    if s >= 85:
        return {"label": "Excellent", "color": "#00C853", "emoji": "🟢"}
    if s >= 70:
        return {"label": "Good", "color": "#64DD17", "emoji": "🟢"}
    if s >= 55:
        return {"label": "Moderate", "color": "#FFAB00", "emoji": "🟡"}
    if s >= 40:
        return {"label": "Weak", "color": "#FF6D00", "emoji": "🟠"}
    return {"label": "Poor", "color": "#D50000", "emoji": "🔴"}


def weighted_score(components: dict, weights: dict) -> int:
    """Compute a weighted percentage from named component scores.

    components: {"keyword": 80, ...}; weights: {"keyword": 0.25, ...}
    Weights are normalized so they do not need to sum to exactly 1.
    """
    total_weight = sum(weights.values()) or 1
    total = 0.0
    for key, weight in weights.items():
        value = components.get(key, 0)
        try:
            total = total + float(value) * (weight / total_weight)
        except (TypeError, ValueError):
            continue
    return round(max(0, min(100, total)))


def priority_rank(items: list, key: str = "priority") -> list:
    """Sort recommendation items by priority order High > Medium > Low."""
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        items,
        key=lambda x: order.get(str(x.get(key, "low")).lower(), 3),
    )
