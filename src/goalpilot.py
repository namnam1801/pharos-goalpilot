#!/usr/bin/env python3
"""
goalpilot.py — Pharos GoalPilot
"Tell me the goal. I'll figure out the transactions."

Usage:
  python src/goalpilot.py --wallet 0x... --goal "I want 500 USDT by tomorrow"
  python src/goalpilot.py --wallet 0x... --goal "reduce my risk" --dry-run
  python src/goalpilot.py --wallet 0x... --network atlantic-testnet
  python src/goalpilot.py --demo

Pharos GoalPilot v1.0.0
MIT-0 License
"""

import sys
import os
import argparse
import json

# Add src/ to path when running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from goal_parser import parse_goal, describe_goal
from wallet_analyzer import analyze_wallet, mock_wallet
from planner import generate_plans
from presenter import (
    present_wallet,
    present_goal,
    present_plans,
    present_confirmation_prompt,
    present_tx_payloads,
    CYAN, BOLD, RESET, DIM, GREEN, YELLOW, RED
)


BANNER = f"""
{CYAN}{BOLD}
  ██████╗  ██████╗  █████╗ ██╗     ██████╗ ██╗██╗      ██████╗ ████████╗
 ██╔════╝ ██╔═══██╗██╔══██╗██║     ██╔══██╗██║██║     ██╔═══██╗╚══██╔══╝
 ██║  ███╗██║   ██║███████║██║     ██████╔╝██║██║     ██║   ██║   ██║   
 ██║   ██║██║   ██║██╔══██║██║     ██╔═══╝ ██║██║     ██║   ██║   ██║   
 ╚██████╔╝╚██████╔╝██║  ██║███████╗██║     ██║███████╗╚██████╔╝   ██║   
  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚══════╝ ╚═════╝    ╚═╝   
{RESET}
  {DIM}Pharos GoalPilot v1.0.0 — "Tell me the goal. I'll figure out the transactions."{RESET}
"""

DEMO_SCENARIOS = [
    ("0xDEMO_Alice", "I want 500 USDT by tomorrow"),
    ("0xDEMO_Bob",   "Reduce my portfolio risk"),
    ("0xDEMO_Carol", "Earn yield with low risk"),
    ("0xDEMO_Dave",  "Prepare my wallet for Blockwave campaign"),
    ("0xDEMO_Eve",   "Turn all idle assets into productive assets"),
]


def assets_dir() -> str:
    """Return path to assets/ relative to project root."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "assets")


def run_scenario(wallet_addr: str, goal_text: str, network: str, dry_run: bool, json_out: bool):
    """Execute one full GoalPilot analysis."""

    # ── Step 1: Parse goal ──
    goal = parse_goal(goal_text)

    if goal.goal_type == "unknown":
        print(f"\n{YELLOW}⚠  Could not parse goal confidently.{RESET}")
        print(f"   Try phrases like: 'I want 500 USDT', 'reduce my risk', 'earn yield'")
        return

    print(present_goal(goal))

    # ── Step 2: Analyze wallet ──
    print(f"\n  {DIM}Fetching wallet state...{RESET}")
    if wallet_addr.startswith("0xDEMO") or dry_run:
        wallet = mock_wallet(wallet_addr)
        print(f"  {DIM}(Using demo wallet — no RPC call){RESET}")
    else:
        wallet = analyze_wallet(wallet_addr, network=network, assets_dir=assets_dir())
        if wallet.error:
            print(f"\n{RED}⚠  Wallet error: {wallet.error}{RESET}")
            print(f"  Falling back to demo wallet for plan generation.\n")
            wallet = mock_wallet(wallet_addr)

    print(present_wallet(wallet))

    # ── Step 3: Generate plans ──
    print(f"\n  {DIM}Analyzing protocols and generating plans...{RESET}")
    plans = generate_plans(goal, wallet, assets_dir=assets_dir())

    # ── Step 4: Present plans ──
    print(present_plans(plans, goal))

    if json_out:
        output = {
            "goal": goal.__dict__,
            "wallet": wallet.summary(),
            "plans": [
                {
                    "plan_id": p.plan_id,
                    "label": p.label,
                    "score": p.score,
                    "expected_apy": p.expected_apy,
                    "risk_after": p.risk_score_after,
                    "outcome": p.outcome_label,
                    "steps": [s.__dict__ for s in p.steps],
                    "warnings": p.warnings,
                }
                for p in plans
            ],
        }
        print("\n" + json.dumps(output, indent=2))
        return

    # ── Step 5: Confirmation gate ──
    if dry_run:
        print(f"  {DIM}[dry-run mode — skipping confirmation]{RESET}\n")
        return

    if not plans:
        return

    top_plan = plans[0]
    print(present_confirmation_prompt(top_plan))

    try:
        choice = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{DIM}Cancelled.{RESET}")
        return

    if choice == "y":
        print(present_tx_payloads(top_plan))
    elif choice == "b" and len(plans) > 1:
        print(present_tx_payloads(plans[1]))
    elif choice == "d":
        print(f"\n{BOLD}Plan {top_plan.plan_id} Details:{RESET}")
        for i, step in enumerate(top_plan.steps, 1):
            print(f"  {i}. {step.description}")
            print(f"     Action: {step.action} | Protocol: {step.protocol}")
    else:
        print(f"\n{DIM}Cancelled. No transactions submitted.{RESET}")


def run_demo():
    """Run all demo scenarios back-to-back."""
    print(BANNER)
    print(f"{CYAN}{BOLD}  DEMO MODE — 5 scenarios{RESET}\n")

    for i, (addr, goal_text) in enumerate(DEMO_SCENARIOS, 1):
        print(f"\n{'═' * 55}")
        print(f"{BOLD}  Scenario {i}/{len(DEMO_SCENARIOS)}{RESET}")
        print(f"{'═' * 55}")
        print(f"  User: \"{goal_text}\"")
        run_scenario(addr, goal_text, "atlantic-testnet", dry_run=True, json_out=False)

        if i < len(DEMO_SCENARIOS):
            print(f"\n  {DIM}[press Enter for next scenario]{RESET}", end="")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass

    print(f"\n{GREEN}{BOLD}  ✓ Demo complete.{RESET}\n")


def interactive_mode(wallet_addr: str, network: str, dry_run: bool):
    """REPL loop — user types goals, agent responds."""
    print(BANNER)
    print(f"  Wallet : {wallet_addr[:6]}...{wallet_addr[-4:] if len(wallet_addr) > 10 else wallet_addr}")
    print(f"  Network: {network}")
    print(f"\n  {DIM}Type your goal (e.g. 'earn yield', 'I want 500 USDT'). Type 'quit' to exit.{RESET}\n")

    while True:
        try:
            goal_text = input(f"{CYAN}GoalPilot>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Goodbye.{RESET}")
            break

        if not goal_text:
            continue
        if goal_text.lower() in ("quit", "exit", "q"):
            print(f"{DIM}Goodbye.{RESET}")
            break

        run_scenario(wallet_addr, goal_text, network, dry_run, json_out=False)
        print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pharos GoalPilot — Goal-driven DeFi planning agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/goalpilot.py --demo
  python src/goalpilot.py --wallet 0x1234... --goal "I want 500 USDT by tomorrow"
  python src/goalpilot.py --wallet 0x1234... --goal "reduce my risk" --dry-run
  python src/goalpilot.py --wallet 0x1234... --network atlantic-testnet
  python src/goalpilot.py --wallet 0x1234... --goal "earn yield" --json
        """
    )
    parser.add_argument("--wallet",  type=str, help="Wallet address (0x...)")
    parser.add_argument("--goal",    type=str, help="Goal in natural language")
    parser.add_argument("--network", type=str, default="mainnet",
                        choices=["mainnet", "atlantic-testnet"],
                        help="Pharos network (default: mainnet)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip confirmation — show plan only, no tx payloads")
    parser.add_argument("--json",    action="store_true",
                        help="Output plan as JSON")
    parser.add_argument("--demo",    action="store_true",
                        help="Run all demo scenarios")

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.wallet:
        parser.print_help()
        print(f"\n{YELLOW}Tip: try --demo to see GoalPilot in action without a wallet.{RESET}\n")
        sys.exit(1)

    if args.goal:
        print(BANNER)
        run_scenario(args.wallet, args.goal, args.network, args.dry_run, args.json)
    else:
        interactive_mode(args.wallet, args.network, args.dry_run)


if __name__ == "__main__":
    main()
