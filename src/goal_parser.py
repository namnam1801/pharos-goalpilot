"""
goal_parser.py — Natural Language Goal → Structured Intent
Pharos GoalPilot v1.0.0

Rule-based parser. No LLM required.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedGoal:
    goal_type: str          # liquidity | yield | risk_reduction | campaign_prep | maximize_apy
    risk_preference: str    # low | medium | high | any
    timeframe_days: Optional[int]
    target_amount: Optional[float]
    target_asset: Optional[str]
    source_hint: Optional[str]      # idle | all | specific asset
    campaign_name: Optional[str]
    raw_text: str
    confidence: float               # 0.0 - 1.0


# ── Keyword tables ──────────────────────────────────────────────────────────

LIQUIDITY_PATTERNS = [
    r"\b(\d+[\d,]*\.?\d*)\s*(usdt|usdc|usd|dollars?)\b",
    r"\bneed\b.*\b(usdt|usdc|cash|liquid)",
    r"\bconvert\b.*\b(usdt|usdc|stable)",
    r"\bcash out\b",
    r"\bliquid\b",
    r"\bwithdraw\b",
]

YIELD_PATTERNS = [
    r"\bearn\b",
    r"\byield\b",
    r"\bapy\b",
    r"\bpassive\b.*\bincome\b",
    r"\bproductive\b",
    r"\bidle\b.*\basset",
    r"\bstake\b",
    r"\bfarm\b",
    r"\bdeposit\b.*\bpool\b",
]

RISK_REDUCTION_PATTERNS = [
    r"\breduce\b.*\brisk\b",
    r"\blower\b.*\brisk\b",
    r"\bsafe[r]?\b",
    r"\bstable\b.*\bportfolio\b",
    r"\bderisking\b",
    r"\bprotect\b.*\bportfolio\b",
    r"\bhedge\b",
]

CAMPAIGN_PATTERNS = [
    r"\bblockwave\b",
    r"\bcampaign\b",
    r"\bpros pixel\b",
    r"\bprospixel\b",
    r"\bprepare\b.*\bcampaign\b",
    r"\bready\b.*\bcampaign\b",
    r"\bparticipate\b.*\bcampaign\b",
]

MAXIMIZE_PATTERNS = [
    r"\bmaximize\b.*\bapy\b",
    r"\bmaximize\b.*\byield\b",
    r"\bbest\b.*\bapy\b",
    r"\bhighest\b.*\byield\b",
    r"\bmost\b.*\byield\b",
]

LOW_RISK_KEYWORDS = [
    r"\blow\s*risk\b", r"\bsafe\b", r"\bstable\b",
    r"\bconservative\b", r"\bsecure\b", r"\bminimal\s*risk\b"
]

HIGH_RISK_KEYWORDS = [
    r"\bhigh\s*risk\b", r"\baggressive\b", r"\bmax\s*yield\b",
    r"\bmaximize\b", r"\bbest\s*return\b", r"\bmost\s*profit\b"
]

TIMEFRAME_PATTERNS = [
    (r"\btoday\b|\bin\s+\d+\s+hours?\b", 0),
    (r"\btomorrow\b|\bby\s+tomorrow\b", 1),
    (r"\bthis\s+week\b|\bin\s+\d+\s+days?\b", 7),
    (r"\bthis\s+month\b|\bin\s+\d+\s+weeks?\b", 30),
]

ASSET_PATTERNS = {
    "USDT": r"\busdt\b",
    "USDC": r"\busdc\b",
    "PHRS": r"\bphrs\b",
    "PROS": r"\bpros\b",
    "WETH": r"\bweth\b|\beth\b",
}

CAMPAIGN_NAMES = {
    "blockwave": r"\bblockwave\b",
    "pros_pixel": r"\bpros\s*pixel\b|\bprospixel\b",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _match_any(text: str, patterns: list) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _extract_amount(text: str) -> Optional[float]:
    """Extract first numeric amount from text."""
    match = re.search(r"\b(\d[\d,]*\.?\d*)\b", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _extract_asset(text: str) -> Optional[str]:
    for asset, pattern in ASSET_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return asset
    return None


def _extract_timeframe(text: str) -> Optional[int]:
    for pattern, days in TIMEFRAME_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return days
    # Try "in X days"
    m = re.search(r"in\s+(\d+)\s+days?", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _extract_campaign(text: str) -> Optional[str]:
    for name, pattern in CAMPAIGN_NAMES.items():
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return None


def _extract_risk(text: str) -> str:
    if _match_any(text, LOW_RISK_KEYWORDS):
        return "low"
    if _match_any(text, HIGH_RISK_KEYWORDS):
        return "high"
    return "medium"


# ── Main Parser ──────────────────────────────────────────────────────────────

def parse_goal(text: str) -> ParsedGoal:
    """
    Parse a natural language goal string into a structured ParsedGoal.

    Examples:
        "I want 500 USDT by tomorrow"
        → ParsedGoal(goal_type='liquidity', target_amount=500, target_asset='USDT', timeframe_days=1)

        "Earn yield with low risk"
        → ParsedGoal(goal_type='yield', risk_preference='low')

        "Reduce my portfolio risk"
        → ParsedGoal(goal_type='risk_reduction')
    """
    t = text.strip()
    confidence = 0.6

    # ── Classify goal type (order matters — most specific first) ──
    if _match_any(t, CAMPAIGN_PATTERNS):
        goal_type = "campaign_prep"
        confidence = 0.85
    elif _match_any(t, MAXIMIZE_PATTERNS):
        goal_type = "maximize_apy"
        confidence = 0.85
    elif _match_any(t, RISK_REDUCTION_PATTERNS):
        goal_type = "risk_reduction"
        confidence = 0.85
    elif _match_any(t, LIQUIDITY_PATTERNS):
        goal_type = "liquidity"
        confidence = 0.90
    elif _match_any(t, YIELD_PATTERNS):
        goal_type = "yield"
        confidence = 0.80
    else:
        goal_type = "unknown"
        confidence = 0.30

    # ── Extract fields ──
    target_amount = _extract_amount(t) if goal_type == "liquidity" else None
    target_asset = _extract_asset(t)
    timeframe = _extract_timeframe(t)
    risk = _extract_risk(t)
    campaign = _extract_campaign(t)
    source = "idle" if re.search(r"\bidle\b", t, re.IGNORECASE) else None

    # Boost confidence if we extracted supporting data
    if target_amount and goal_type == "liquidity":
        confidence = min(confidence + 0.05, 0.99)
    if campaign and goal_type == "campaign_prep":
        confidence = min(confidence + 0.05, 0.99)

    return ParsedGoal(
        goal_type=goal_type,
        risk_preference=risk,
        timeframe_days=timeframe,
        target_amount=target_amount,
        target_asset=target_asset or ("USDT" if goal_type == "liquidity" else None),
        source_hint=source,
        campaign_name=campaign,
        raw_text=t,
        confidence=confidence,
    )


def describe_goal(g: ParsedGoal) -> str:
    """Return a one-line human-readable description of the parsed goal."""
    type_labels = {
        "liquidity": "Liquidity",
        "yield": "Yield Generation",
        "risk_reduction": "Risk Reduction",
        "campaign_prep": "Campaign Preparation",
        "maximize_apy": "Maximize APY",
        "unknown": "General Goal",
    }
    label = type_labels.get(g.goal_type, g.goal_type)

    parts = [label]
    if g.target_amount and g.target_asset:
        parts.append(f"— {g.target_amount:,.0f} {g.target_asset}")
    if g.timeframe_days is not None:
        if g.timeframe_days == 0:
            parts.append("(today)")
        elif g.timeframe_days == 1:
            parts.append("(by tomorrow)")
        else:
            parts.append(f"(within {g.timeframe_days} days)")
    if g.risk_preference != "medium":
        parts.append(f"[{g.risk_preference} risk]")
    if g.campaign_name:
        parts.append(f"for {g.campaign_name}")

    return " ".join(parts)


# ── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        "I want 500 USDT by tomorrow",
        "Reduce my portfolio risk",
        "Earn yield with low risk",
        "Turn all idle assets into productive assets",
        "Prepare my wallet for Blockwave campaign",
        "Maximize my APY",
        "I need some liquid cash today",
    ]
    for t in test_cases:
        g = parse_goal(t)
        print(f'Input : "{t}"')
        print(f'Result: {describe_goal(g)} (confidence={g.confidence:.0%})')
        print()
