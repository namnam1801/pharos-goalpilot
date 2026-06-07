# Pharos GoalPilot 🧭

> **"Tell me the goal. I'll figure out the transactions."**

Pharos GoalPilot is a goal-driven AI agent skill for the [Pharos Agent Center](https://www.pharos.xyz/agent-center). Instead of commanding a transaction, you tell the agent what you *want to achieve* — in plain English. The agent analyzes your wallet, generates ranked multi-step action plans, and asks for confirmation before returning any transaction payloads.

---

## Why GoalPilot is Different

Most DeFi skills are one-step command executors:

```
User command → Transaction
```

GoalPilot operates at a higher level of abstraction:

```
User goal (natural language)
    ↓
Goal Parser       → structured intent
    ↓
Wallet Analyzer   → current portfolio snapshot
    ↓
Planner Engine    → ranked action plans (A / B / C)
    ↓
Plan Presenter    → human-readable output with scores
    ↓
Confirmation Gate → user approves → transaction payloads
```

This is the closest thing to a true AI agent on Pharos.

---

## Demo

```bash
pip install requests
python src/goalpilot.py --demo
```

This runs 5 showcase scenarios with a mock wallet — no RPC, no address needed.

[![Demo](demo/demo_screenshot.png)](demo/playbook.md)

---

## Supported Goals

| You say | GoalPilot does |
|---|---|
| `"I want 500 USDT by tomorrow"` | Calculates swap path to hit liquidity target |
| `"Reduce my portfolio risk"` | Recommends moving volatile → stablecoins |
| `"Earn yield with low risk"` | Picks safest yield protocol for your assets |
| `"Turn idle assets into productive ones"` | Routes idle PHRS/PROS into yield strategies |
| `"Prepare my wallet for Blockwave campaign"` | Checks readiness + stakes for campaign points |
| `"Maximize my APY"` | Multi-protocol yield stacking with risk warning |

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/pharos-goalpilot
cd pharos-goalpilot
pip install -r requirements.txt
```

**Or via Pharos Skill Engine:**
```bash
npx skills add https://github.com/YOUR_USERNAME/pharos-goalpilot
```

---

## Usage

### Demo mode (no wallet needed)
```bash
python src/goalpilot.py --demo
```

### One-shot goal
```bash
python src/goalpilot.py --wallet 0x1234... --goal "I want 500 USDT by tomorrow"
```

### Dry-run (plan only, no confirmation)
```bash
python src/goalpilot.py --wallet 0x1234... --goal "reduce my risk" --dry-run
```

### JSON output (for agent pipelines)
```bash
python src/goalpilot.py --wallet 0x1234... --goal "earn yield" --dry-run --json
```

### Interactive REPL
```bash
python src/goalpilot.py --wallet 0x1234...
# GoalPilot> I want 500 USDT by tomorrow
# GoalPilot> earn yield with low risk
```

### Testnet
```bash
python src/goalpilot.py --wallet 0x1234... --network atlantic-testnet
```

---

## How Plans Are Scored

Each plan receives a **score 0–100** based on how well it serves the goal:

| Goal type | Score weights |
|---|---|
| Liquidity | Outcome match (50%) + Feasibility (30%) + Risk (20%) |
| Yield | APY (45%) + Risk (35%) + Feasibility (20%) |
| Risk reduction | Risk improvement (60%) + Feasibility (30%) + APY (10%) |
| Campaign prep | Feasibility (60%) + Risk (30%) + APY (10%) |
| Maximize APY | APY (60%) + Feasibility (25%) + Risk (15%) |

The agent always recommends the highest-scoring plan but presents alternatives so the user can choose.

---

## Sample Output

```
═══════════════════════════════════════════════════
  🎯 Goal Detected
  Liquidity — 500 USDT (by tomorrow)
  Confidence: ★★★★☆ (85%)

  📊 Wallet Snapshot
  PHRS    320.00  ($166.40)
  USDT    180.00  ($180.00)
  Total   $391.40
  Risk Score: 54/100  ██████████░░░░░░░░░░

  📋 Recommended Plans

★ Plan A — Recommended — Simplest Path      Score: 89/100
  1. Swap 240.00 PHRS → USDT via Pharos Port Swap
  2. Hold 304 USDT total
  Expected outcome : ~304 USDT (target: 500)
  APY              : 0%
  Risk after       : Low (34/100)
  Score            : 89/100  ██████████████████░░

  Plan B — Alternative — Keep PHRS + Borrow  Score: 61/100
  1. Deposit 128.00 PHRS as collateral on FaroSwap
  2. Swap 64.00 PHRS → USDT for liquidity
  Expected outcome : ~262 USDT + LP position
  APY              : 4.5%
  Risk after       : High (64/100)
  Score            : 61/100  ████████████░░░░░░░░

Proceed with Plan A? [y/n/b/d]
```

---

## Architecture

```
pharos-goalpilot/
├── SKILL.md                    ← Pharos Skill Engine entry point
├── README.md
├── requirements.txt
├── src/
│   ├── goalpilot.py            ← Main entry point + CLI
│   ├── goal_parser.py          ← NL goal → structured intent
│   ├── wallet_analyzer.py      ← Fetch + classify wallet state
│   ├── planner.py              ← Generate + score action plans
│   └── presenter.py            ← Human-readable output
├── assets/
│   ├── networks.json           ← Pharos RPC config (Skill Engine spec)
│   └── protocols.json          ← Protocol registry + APY data
└── demo/
    └── playbook.md             ← 20+ sample prompts + scenarios
```

---

## Networks

| Network | Chain ID | RPC |
|---|---|---|
| Pharos Mainnet | 1672 | https://rpc.pharos.xyz |
| Atlantic Testnet | 688689 | https://atlantic.dplabs-internal.com |

---

## Safety

- **Read-only by default** — no private key required
- **Dry-run mode** — `--dry-run` shows plan without prompting
- **Confirmation gate** — user must approve before payloads are shown
- **No signing** — GoalPilot returns transaction descriptions only; your wallet signs
- **No funds moved** — the skill never initiates transactions

---

## Dependencies

- Python 3.9+
- `requests` — RPC calls
- `web3` *(optional)* — for LP position detection

---

## Supported Framework

Pharos Skill Engine (Claude Code). Compatible with:
- Claude Code CLI
- Pharos Agent Center
- Any JSON-RPC compatible Pharos node

---

## License

MIT-0 — No attribution required.

---

## Links

- Pharos Agent Center: https://www.pharos.xyz/agent-center
- Pharos Port: https://port.pharos.xyz
- FaroSwap: https://docs.faroswap.xyz
- Pharos Harbor: https://port.pharos.xyz/harbor
- Blockwave Campaign: https://port.pharos.xyz/blockwaver
- PROS Pixel: https://prospixel.xyz
- Demo Playbook: [demo/playbook.md](demo/playbook.md)
