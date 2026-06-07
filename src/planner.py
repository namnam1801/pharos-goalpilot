"""
planner.py — Goal-driven Action Plan Generator & Scorer
Pharos GoalPilot v1.0.0

Input : ParsedGoal + WalletSnapshot
Output: List[ActionPlan] sorted by score descending
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional

from goal_parser import ParsedGoal
from wallet_analyzer import WalletSnapshot


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class PlanStep:
    action: str             # "swap" | "stake" | "deposit" | "unstake" | "hold" | "participate"
    protocol: str
    from_asset: Optional[str]
    to_asset: Optional[str]
    amount: Optional[float]
    amount_unit: Optional[str]   # "PHRS" | "USDT" | "%" | "all"
    description: str             # human-readable


@dataclass
class ActionPlan:
    plan_id: str            # "A" | "B" | "C"
    label: str              # "Recommended" | "Alternative" | "Aggressive"
    steps: List[PlanStep]
    expected_apy: float     # %
    expected_outcome_usd: float
    risk_score_after: int   # 0–100
    score: int              # 0–100 composite
    outcome_label: str      # human summary of what happens
    risk_label: str         # "Low" | "Medium" | "High"
    warnings: List[str] = field(default_factory=list)


# ── Scoring formula ───────────────────────────────────────────────────────────

def _score_plan(
    goal: ParsedGoal,
    apy: float,
    risk_after: int,
    feasibility: float,      # 0.0–1.0
    outcome_ratio: float,    # how close to goal (0.0–1.0)
) -> int:
    """
    Composite score 0–100 weighting goal alignment, risk, yield, feasibility.

    Weights depend on goal type:
    - liquidity    : outcome (50%) + feasibility (30%) + risk (20%)
    - yield        : apy (45%) + risk (35%) + feasibility (20%)
    - risk_red     : risk (60%) + feasibility (30%) + apy (10%)
    - campaign_prep: feasibility (60%) + risk (30%) + apy (10%)
    - maximize_apy : apy (60%) + feasibility (25%) + risk (15%)
    """
    # Normalize risk (lower is better → invert)
    risk_score_norm = (100 - risk_after) / 100  # 0–1

    # Normalize APY (cap at 25%)
    apy_norm = min(apy / 25.0, 1.0)

    weights = {
        "liquidity":     (0.50, 0.30, 0.20, 0.00),  # outcome, feas, risk, apy
        "yield":         (0.10, 0.20, 0.35, 0.45),
        "risk_reduction":(0.00, 0.30, 0.60, 0.10),
        "campaign_prep": (0.10, 0.60, 0.30, 0.00),
        "maximize_apy":  (0.00, 0.25, 0.15, 0.60),
    }.get(goal.goal_type, (0.25, 0.25, 0.25, 0.25))

    raw = (
        weights[0] * outcome_ratio +
        weights[1] * feasibility +
        weights[2] * risk_score_norm +
        weights[3] * apy_norm
    )
    return max(0, min(100, int(raw * 100)))


def _risk_label(score: int) -> str:
    if score < 25:
        return "Low"
    if score < 55:
        return "Medium"
    if score < 75:
        return "High"
    return "Very High"


def _apy_label(apy: float) -> str:
    if apy == 0:
        return "0% (no yield)"
    return f"{apy:.1f}%"


# ── Plan generators (one per goal type) ──────────────────────────────────────

def _plan_liquidity(goal: ParsedGoal, wallet: WalletSnapshot, protocols: dict) -> List[ActionPlan]:
    target = goal.target_amount or 200.0
    current_stable = wallet.stablecoin_usd
    shortfall = max(0, target - current_stable)
    phrs_price = 0.52   # from assets/protocols.json

    plans = []

    # ── Plan A: Sell PHRS to cover shortfall ──
    phrs_needed = shortfall / phrs_price
    phrs_available = wallet.native_phrs
    phrs_to_sell = min(phrs_needed * 1.05, phrs_available * 0.90)  # keep 10% for gas
    proceeds = phrs_to_sell * phrs_price
    total_stable_a = current_stable + proceeds
    feasibility_a = min(total_stable_a / target, 1.0)
    risk_a = max(10, wallet.risk_score - int(feasibility_a * 25))

    plan_a = ActionPlan(
        plan_id="A",
        label="Recommended — Simplest Path",
        steps=[
            PlanStep("swap", "Pharos Port Swap",
                     "PHRS", "USDT", round(phrs_to_sell, 2), "PHRS",
                     f"Swap {phrs_to_sell:.2f} PHRS → USDT via Pharos Port Swap"),
            PlanStep("hold", "Wallet",
                     None, None, None, None,
                     f"Hold {total_stable_a:.0f} USDT total"),
        ],
        expected_apy=0.0,
        expected_outcome_usd=total_stable_a,
        risk_score_after=risk_a,
        score=0,
        outcome_label=f"~{total_stable_a:.0f} USDT (target: {target:.0f})",
        risk_label=_risk_label(risk_a),
        warnings=([] if total_stable_a >= target else
                  [f"Shortfall: {target - total_stable_a:.0f} USDT — sell more PHRS to fully cover"]),
    )
    plan_a.score = _score_plan(goal, 0, risk_a, feasibility_a, feasibility_a)
    plans.append(plan_a)

    # ── Plan B: Use yield + partial swap ──
    deposit_phrs = wallet.native_phrs * 0.4
    borrow_usd = deposit_phrs * phrs_price * 0.6  # ~60% LTV proxy
    total_stable_b = current_stable + borrow_usd
    feasibility_b = min(total_stable_b / target, 1.0)
    risk_b = wallet.risk_score + 10  # borrowing adds risk

    plan_b = ActionPlan(
        plan_id="B",
        label="Alternative — Keep PHRS + Borrow",
        steps=[
            PlanStep("deposit", "FaroSwap",
                     "PHRS", None, round(deposit_phrs, 2), "PHRS",
                     f"Deposit {deposit_phrs:.2f} PHRS as collateral on FaroSwap"),
            PlanStep("swap", "Pharos Port Swap",
                     "PHRS", "USDT", round(wallet.native_phrs * 0.2, 2), "PHRS",
                     f"Swap {wallet.native_phrs * 0.2:.2f} PHRS → USDT for liquidity"),
        ],
        expected_apy=4.5,
        expected_outcome_usd=total_stable_b,
        risk_score_after=min(100, risk_b),
        score=0,
        outcome_label=f"~{total_stable_b:.0f} USDT + LP position",
        risk_label=_risk_label(min(100, risk_b)),
        warnings=["Higher complexity — LP position requires monitoring"],
    )
    plan_b.score = _score_plan(goal, 4.5, risk_b, feasibility_b, feasibility_b)
    plans.append(plan_b)

    return sorted(plans, key=lambda p: p.score, reverse=True)


def _plan_yield(goal: ParsedGoal, wallet: WalletSnapshot, protocols: dict) -> List[ActionPlan]:
    idle = wallet.idle_usd
    phrs = wallet.native_phrs

    plans = []

    # ── Plan A: Stake idle PHRS → Harbor (low risk) ──
    if goal.risk_preference in ("low", "medium"):
        phrs_to_stake = phrs * 0.80
        apy_a = 9.5
        plan_a = ActionPlan(
            plan_id="A",
            label="Conservative — Harbor Vault",
            steps=[
                PlanStep("stake", "Pharos Harbor",
                         "PHRS", None, round(phrs_to_stake, 2), "PHRS",
                         f"Deposit {phrs_to_stake:.2f} PHRS into Pharos Harbor vault"),
            ],
            expected_apy=apy_a,
            expected_outcome_usd=idle * (1 + apy_a / 100 / 12),  # 1-month est
            risk_score_after=max(10, wallet.risk_score - 20),
            score=0,
            outcome_label=f"~{apy_a}% APY on PHRS holdings",
            risk_label="Low",
        )
        plan_a.score = _score_plan(goal, apy_a, plan_a.risk_score_after, 0.9, 0.8)
        plans.append(plan_a)

    # ── Plan B: FaroSwap LP (higher yield, more risk) ──
    apy_b = 14.2
    plan_b = ActionPlan(
        plan_id="B",
        label="Balanced — FaroSwap LP",
        steps=[
            PlanStep("swap", "Pharos Port Swap",
                     "PHRS", "USDT", round(phrs * 0.4, 2), "PHRS",
                     f"Swap {phrs * 0.4:.2f} PHRS → USDT (50/50 prep)"),
            PlanStep("deposit", "FaroSwap",
                     "PHRS+USDT", None, None, "50/50",
                     "Add PHRS/USDT liquidity to FaroSwap pool"),
        ],
        expected_apy=apy_b,
        expected_outcome_usd=idle * (1 + apy_b / 100 / 12),
        risk_score_after=wallet.risk_score + 5,
        score=0,
        outcome_label=f"~{apy_b}% APY (LP fees + rewards)",
        risk_label="Medium",
        warnings=["Impermanent loss risk if PHRS price moves significantly"],
    )
    plan_b.score = _score_plan(goal, apy_b, plan_b.risk_score_after, 0.85, 0.85)
    plans.append(plan_b)

    # ── Plan C: Maximize (only if high risk ok) ──
    if goal.risk_preference in ("high", "any", "medium"):
        apy_c = 18.0
        plan_c = ActionPlan(
            plan_id="C",
            label="Aggressive — Max Yield",
            steps=[
                PlanStep("stake", "Pharos Harbor",
                         "PHRS", None, round(phrs * 0.5, 2), "PHRS",
                         f"Stake {phrs * 0.5:.2f} PHRS in Harbor"),
                PlanStep("deposit", "FaroSwap",
                         "PHRS", None, round(phrs * 0.3, 2), "PHRS",
                         f"Deploy {phrs * 0.3:.2f} PHRS to FaroSwap LP"),
                PlanStep("stake", "PROS Pixel",
                         "PROS", None, None, "all",
                         "Stake all PROS in PROS Pixel for campaign bonus"),
            ],
            expected_apy=apy_c,
            expected_outcome_usd=idle * (1 + apy_c / 100 / 12),
            risk_score_after=min(100, wallet.risk_score + 20),
            score=0,
            outcome_label=f"~{apy_c}% blended APY",
            risk_label="High",
            warnings=["High complexity", "Multiple protocol exposure", "Requires active monitoring"],
        )
        plan_c.score = _score_plan(goal, apy_c, plan_c.risk_score_after, 0.75, 0.9)
        plans.append(plan_c)

    return sorted(plans, key=lambda p: p.score, reverse=True)


def _plan_risk_reduction(goal: ParsedGoal, wallet: WalletSnapshot, protocols: dict) -> List[ActionPlan]:
    volatile = wallet.volatile_usd
    current_risk = wallet.risk_score
    phrs = wallet.native_phrs

    # Move 40% of volatile → stablecoins
    phrs_to_sell_a = phrs * 0.40
    proceeds_a = phrs_to_sell_a * 0.52
    new_risk_a = max(5, current_risk - 30)

    plan_a = ActionPlan(
        plan_id="A",
        label="Recommended — Partial De-risk",
        steps=[
            PlanStep("swap", "Pharos Port Swap",
                     "PHRS", "USDT", round(phrs_to_sell_a, 2), "PHRS",
                     f"Swap {phrs_to_sell_a:.2f} PHRS → USDT (40% of volatile)"),
        ],
        expected_apy=0.0,
        expected_outcome_usd=wallet.total_usd,
        risk_score_after=new_risk_a,
        score=0,
        outcome_label=f"Risk score: {current_risk} → {new_risk_a}",
        risk_label=_risk_label(new_risk_a),
    )
    plan_a.score = _score_plan(goal, 0, new_risk_a, 0.95, 1.0)

    # More aggressive de-risk: 70% → stable
    phrs_to_sell_b = phrs * 0.70
    proceeds_b = phrs_to_sell_b * 0.52
    new_risk_b = max(5, current_risk - 55)

    plan_b = ActionPlan(
        plan_id="B",
        label="Aggressive De-risk",
        steps=[
            PlanStep("swap", "Pharos Port Swap",
                     "PHRS", "USDT", round(phrs_to_sell_b, 2), "PHRS",
                     f"Swap {phrs_to_sell_b:.2f} PHRS → USDT (70% of holdings)"),
            PlanStep("stake", "Pharos Harbor",
                     "USDT", None, None, "50%",
                     "Deposit 50% of USDT into Harbor for 6% APY"),
        ],
        expected_apy=3.0,
        expected_outcome_usd=wallet.total_usd,
        risk_score_after=new_risk_b,
        score=0,
        outcome_label=f"Risk score: {current_risk} → {new_risk_b} + 3% APY",
        risk_label=_risk_label(new_risk_b),
    )
    plan_b.score = _score_plan(goal, 3.0, new_risk_b, 0.85, 1.0)

    return sorted([plan_a, plan_b], key=lambda p: p.score, reverse=True)


def _plan_campaign(goal: ParsedGoal, wallet: WalletSnapshot, protocols: dict) -> List[ActionPlan]:
    campaign = goal.campaign_name or "blockwave"
    phrs = wallet.native_phrs
    pros_balance = wallet.tokens.get("PROS", None)
    pros_amount = pros_balance.amount if pros_balance else 0

    steps = []

    # Ensure some PHRS for gas
    if phrs < 5:
        steps.append(PlanStep("hold", "Wallet", None, None, None, None,
                              "⚠️ Low PHRS — bridge or acquire more for gas"))

    if campaign == "blockwave":
        steps.append(PlanStep("participate", "Blockwave Campaign",
                              None, None, None, None,
                              "Connect wallet to https://port.pharos.xyz/blockwaver"))
        steps.append(PlanStep("stake", "Pharos Harbor",
                              "PHRS", None, round(phrs * 0.5, 2), "PHRS",
                              f"Stake {phrs * 0.5:.2f} PHRS for Blockwave points"))
        if pros_amount > 0:
            steps.append(PlanStep("stake", "PROS Pixel",
                                  "PROS", None, pros_amount, "PROS",
                                  f"Stake {pros_amount:.0f} PROS on prospixel.xyz"))

    plan_a = ActionPlan(
        plan_id="A",
        label=f"Campaign Prep — {campaign.title()}",
        steps=steps,
        expected_apy=0.0,
        expected_outcome_usd=wallet.total_usd,
        risk_score_after=max(10, wallet.risk_score - 5),
        score=0,
        outcome_label=f"Wallet ready for {campaign} campaign",
        risk_label="Low",
    )
    plan_a.score = _score_plan(goal, 0, plan_a.risk_score_after, 0.95, 1.0)

    return [plan_a]


# ── Main planner ──────────────────────────────────────────────────────────────

def generate_plans(
    goal: ParsedGoal,
    wallet: WalletSnapshot,
    assets_dir: str = "assets",
) -> List[ActionPlan]:
    """
    Generate ranked action plans for the given goal and wallet state.

    Returns a list of ActionPlan sorted by score (highest first).
    """
    try:
        with open(f"{assets_dir}/protocols.json") as f:
            protocols = json.load(f)
    except Exception:
        protocols = {}

    dispatch = {
        "liquidity":     _plan_liquidity,
        "yield":         _plan_yield,
        "risk_reduction":_plan_risk_reduction,
        "campaign_prep": _plan_campaign,
        "maximize_apy":  lambda g, w, p: _plan_yield(
            ParsedGoal(**{**g.__dict__, "risk_preference": "high"}), w, p
        ),
    }

    fn = dispatch.get(goal.goal_type)
    if fn is None:
        # Fallback: generic yield plan
        return _plan_yield(goal, wallet, protocols)

    return fn(goal, wallet, protocols)
