"""
presenter.py — Human-Readable Plan Output Formatter
Pharos GoalPilot v1.0.0
"""

from typing import List
from wallet_analyzer import WalletSnapshot
from goal_parser import ParsedGoal, describe_goal
from planner import ActionPlan


# ANSI colors (degrade gracefully in non-color terminals)
BOLD   = "\033[1m"
RESET  = "\033[0m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
DIM    = "\033[2m"
BLUE   = "\033[94m"


def _bar(score: int, width: int = 20) -> str:
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _risk_color(label: str) -> str:
    return {
        "Low": GREEN,
        "Medium": YELLOW,
        "High": RED,
        "Very High": RED,
    }.get(label, RESET)


def present_wallet(wallet: WalletSnapshot) -> str:
    lines = [
        f"\n{BOLD}{'─' * 50}{RESET}",
        f"{CYAN}{BOLD}  📊 Wallet Snapshot{RESET}",
        f"{BOLD}{'─' * 50}{RESET}",
        f"  Address : {DIM}{wallet.address[:6]}...{wallet.address[-4:]}{RESET}",
        f"  Network : {wallet.network}",
        "",
        f"  {BOLD}PHRS{RESET}    {wallet.native_phrs:>10.2f}  (${wallet.native_usd:,.2f})",
    ]
    for symbol, tb in wallet.tokens.items():
        lines.append(f"  {BOLD}{symbol}{RESET}    {tb.amount:>10.2f}  (${tb.usd_value:,.2f})")

    lines += [
        "",
        f"  {'Total USD':<14}  ${wallet.total_usd:,.2f}",
        f"  {'Stablecoins':<14}  ${wallet.stablecoin_usd:,.2f}",
        f"  {'Volatile':<14}  ${wallet.volatile_usd:,.2f}",
        f"  {'Idle assets':<14}  ${wallet.idle_usd:,.2f}",
        "",
        f"  Risk Score  {_risk_color(_risk_label(wallet.risk_score))}{BOLD}{wallet.risk_score}/100{RESET}  {_bar(wallet.risk_score)}",
    ]
    return "\n".join(lines)


def _risk_label(score: int) -> str:
    if score < 25: return "Low"
    if score < 55: return "Medium"
    if score < 75: return "High"
    return "Very High"


def present_goal(goal: ParsedGoal) -> str:
    conf_bar = "★" * int(goal.confidence * 5) + "☆" * (5 - int(goal.confidence * 5))
    return (
        f"\n{BOLD}{'─' * 50}{RESET}\n"
        f"{CYAN}{BOLD}  🎯 Goal Detected{RESET}\n"
        f"{BOLD}{'─' * 50}{RESET}\n"
        f"  {BOLD}{describe_goal(goal)}{RESET}\n"
        f"  Confidence: {conf_bar} ({goal.confidence:.0%})\n"
    )


def present_plans(plans: List[ActionPlan], goal: ParsedGoal) -> str:
    if not plans:
        return f"\n{RED}No plans could be generated for this goal.{RESET}\n"

    lines = [
        f"\n{BOLD}{'─' * 50}{RESET}",
        f"{CYAN}{BOLD}  📋 Recommended Plans{RESET}",
        f"{BOLD}{'─' * 50}{RESET}",
    ]

    for i, plan in enumerate(plans):
        is_top = i == 0
        marker = f"{GREEN}★ " if is_top else "  "
        score_color = GREEN if plan.score >= 75 else (YELLOW if plan.score >= 50 else RED)

        lines += [
            "",
            f"  {marker}{BOLD}Plan {plan.plan_id}{RESET} — {plan.label}",
            f"  {'─' * 46}",
        ]

        for j, step in enumerate(plan.steps, 1):
            lines.append(f"  {DIM}{j}.{RESET} {step.description}")

        risk_col = _risk_color(plan.risk_label)

        lines += [
            "",
            f"  Expected outcome : {BOLD}{plan.outcome_label}{RESET}",
            f"  APY              : {BOLD}{plan.expected_apy:.1f}%{RESET}" if plan.expected_apy > 0
            else f"  APY              : {DIM}0% (no yield){RESET}",
            f"  Risk after       : {risk_col}{BOLD}{plan.risk_label} ({plan.risk_score_after}/100){RESET}",
            f"  Score            : {score_color}{BOLD}{plan.score}/100{RESET}  {_bar(plan.score)}",
        ]

        if plan.warnings:
            lines.append(f"  {YELLOW}⚠  " + "  ⚠  ".join(plan.warnings) + RESET)

    lines += [
        "",
        f"{BOLD}{'─' * 50}{RESET}",
    ]
    return "\n".join(lines)


def present_confirmation_prompt(top_plan: ActionPlan) -> str:
    return (
        f"\n{BOLD}Proceed with Plan {top_plan.plan_id}?{RESET}\n"
        f"  [y] Yes — show transaction payloads\n"
        f"  [n] No  — cancel\n"
        f"  [b] Show Plan B instead\n"
        f"  [d] Details / explain more\n"
        f"\n  > "
    )


def present_tx_payloads(plan: ActionPlan) -> str:
    lines = [
        f"\n{CYAN}{BOLD}  🔐 Transaction Payloads — Plan {plan.plan_id}{RESET}",
        f"{BOLD}{'─' * 50}{RESET}",
        f"{YELLOW}  ⚠  Review carefully before signing. GoalPilot never signs transactions.{RESET}",
        "",
    ]
    for i, step in enumerate(plan.steps, 1):
        lines += [
            f"  {BOLD}Step {i}: {step.action.upper()} via {step.protocol}{RESET}",
            f"  {step.description}",
        ]
        if step.action == "swap" and step.from_asset and step.to_asset:
            lines += [
                f"  → Navigate to: https://port.pharos.xyz/swap",
                f"  → From: {step.amount} {step.from_asset}",
                f"  → To  : {step.to_asset}",
            ]
        elif step.action in ("stake", "deposit"):
            lines += [
                f"  → Navigate to: https://port.pharos.xyz/harbor",
                f"  → Amount: {step.amount} {step.amount_unit or ''}",
            ]
        elif step.action == "participate":
            lines.append(f"  → Navigate to: https://port.pharos.xyz/blockwaver")
        lines.append("")

    lines.append(f"{DIM}  Note: All actions are on Pharos network. Ensure wallet is connected to Chain ID 1672 (mainnet) or 688689 (testnet).{RESET}")
    return "\n".join(lines)
