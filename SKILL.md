---
name: pharos-goalpilot
description: >
  Goal-driven AI agent skill for Pharos. Use this skill when a user expresses
  a financial goal, desired outcome, or portfolio intent in natural language —
  such as "I want 500 USDT by tomorrow", "reduce my risk", "earn yield with low risk",
  or "prepare my wallet for Blockwave". The skill analyzes the wallet, parses the goal,
  generates a ranked multi-step action plan, and asks for confirmation before execution.
  Do NOT use for single-command transactions (swap, stake, send). USE this skill whenever
  the user describes what they WANT rather than what they want to DO.
---

# Pharos GoalPilot

> **"Tell me the goal. I'll figure out the transactions."**

GoalPilot is a goal-driven planning agent for the Pharos ecosystem. Unlike command-based skills that map one input to one transaction, GoalPilot accepts high-level financial goals expressed in natural language, analyzes the user's wallet state, generates a scored multi-step action plan, and guides the user to confirm before any action is taken.

---

## Architecture

```
User Goal (natural language)
        ↓
  [1] Goal Parser        → structured intent {goal, risk, timeframe, amount}
        ↓
  [2] Wallet Analyzer    → current portfolio snapshot
        ↓
  [3] Planner Engine     → ranked action plans (A / B / C)
        ↓
  [4] Plan Presenter     → human-readable output with scores
        ↓
  [5] Confirmation Gate  → user approves → transaction payloads returned
```

---

## Usage

Run the agent:
```bash
python src/goalpilot.py --wallet 0xYourAddress --goal "I want 500 USDT by tomorrow"
```

Or interactive mode:
```bash
python src/goalpilot.py --wallet 0xYourAddress
# Then type your goal when prompted
```

Dry-run (no transactions, just the plan):
```bash
python src/goalpilot.py --wallet 0xYourAddress --goal "reduce my portfolio risk" --dry-run
```

---

## Supported Goal Types

| User says | Parsed intent |
|---|---|
| "I want 500 USDT by tomorrow" | `{goal: liquidity, target: 500, asset: USDT, timeframe: 1d}` |
| "Reduce my portfolio risk" | `{goal: risk_reduction}` |
| "Earn yield with low risk" | `{goal: yield, risk: low}` |
| "Turn idle assets into productive ones" | `{goal: yield, source: idle}` |
| "Prepare wallet for Blockwave campaign" | `{goal: campaign_prep, campaign: blockwave}` |
| "Maximize my APY" | `{goal: yield, risk: any}` |

---

## Output Format

Each plan includes:

```
=== GoalPilot Analysis ===

Wallet Snapshot:
  PHRS:   320.00  (~$160)
  USDT:   180.00
  Idle:   120.00 PHRS (not earning)
  Risk Score: 68 / 100

Goal Detected: Liquidity — 500 USDT in 1 day

── Plan A (Recommended) ──────────────── Score: 89
  Step 1: Swap 200 PHRS → USDT  (est. $198)
  Step 2: Hold total 378 USDT
  Expected outcome: ~378 USDT (shortfall: 122)
  Risk after: 34    Yield: 0%

── Plan B ────────────────────────────── Score: 61
  Step 1: Deposit 120 PHRS → FaroSwap Pool
  Step 2: Borrow 200 USDT against collateral
  Expected outcome: 380 USDT + LP position
  Risk after: 72    APY: 4.2%

Proceed with Plan A? [y/n/details]
```

---

## Dependencies

- Python 3.9+
- `requests` — RPC calls
- `web3` — ABI decoding (optional, for LP positions)
- Pharos RPC: `https://rpc.pharos.xyz` (mainnet) or `https://atlantic.dplabs-internal.com` (testnet)

Install:
```bash
pip install -r requirements.txt
```

---

## Networks

| Network | Chain ID | RPC |
|---|---|---|
| Pharos Mainnet | 1672 | https://rpc.pharos.xyz |
| Atlantic Testnet | 688689 | https://atlantic.dplabs-internal.com |

---

## Safety

- **Read-only by default** — no private keys required for planning
- **Dry-run gate** — `--dry-run` flag skips all confirmation prompts
- **Confirmation required** — user must type `y` before any payload is returned
- **No funds moved** — the skill returns transaction payloads only; signing is always the user's responsibility

---

## Files

| Path | Purpose |
|---|---|
| `src/goalpilot.py` | Main entry point |
| `src/goal_parser.py` | Natural language → structured intent |
| `src/wallet_analyzer.py` | Fetch and classify wallet assets |
| `src/planner.py` | Generate and score action plans |
| `src/presenter.py` | Format plan output |
| `assets/protocols.json` | Known Pharos protocols + APY data |
| `assets/networks.json` | RPC endpoints (Skill Engine spec) |
| `demo/playbook.md` | 20+ sample prompts |

---

## License

MIT-0 — No attribution required.
