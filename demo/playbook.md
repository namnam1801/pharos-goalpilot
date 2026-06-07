# Pharos GoalPilot — Demo Playbook

> 20+ sample prompts + 5-minute end-to-end scenario

---

## Quick Start (no wallet needed)

```bash
python src/goalpilot.py --demo
```

Runs all 5 showcase scenarios automatically.

---

## Sample Prompts

### 🏦 Liquidity Goals

```
I want 500 USDT by tomorrow
```
```
I need 200 USDT today
```
```
Get me liquid, I need 1000 dollars by end of week
```
```
Convert my PHRS to stablecoins
```
```
Cash out some of my portfolio
```

### 📈 Yield Goals

```
Earn yield with low risk
```
```
Turn all idle assets into productive assets
```
```
I want passive income from my wallet
```
```
Best yield farming strategy with medium risk
```
```
Stake my PHRS somewhere safe
```
```
Help me farm with my idle PHRS
```

### 🛡️ Risk Goals

```
Reduce my portfolio risk
```
```
My portfolio is too risky, help me fix it
```
```
Move to safer assets
```
```
I want a more conservative portfolio
```
```
Protect my holdings from volatility
```

### 🏆 Campaign Goals

```
Prepare my wallet for Blockwave campaign
```
```
Help me participate in the current Pharos campaign
```
```
Get me ready for PROS Pixel
```
```
I want to join Blockwave, what do I need?
```

### ⚡ Maximize Goals

```
Maximize my APY
```
```
Give me the highest yield possible
```
```
Best returns on my PHRS
```

---

## 5-Minute End-to-End Scenario

### Setup
```bash
pip install requests
python src/goalpilot.py --demo
```

### Scenario 1: "I need 500 USDT tomorrow"

**Input wallet** (mock):
- 320 PHRS (~$166)
- 180 USDT
- 250 PROS (~$45)
- Total: ~$391

**GoalPilot output:**
```
🎯 Goal Detected
  Liquidity — 500 USDT (by tomorrow) [medium risk]

📊 Wallet Snapshot
  PHRS    320.00  ($166.40)
  USDT    180.00  ($180.00)
  PROS    250.00  ($45.00)
  Total   $391.40
  Risk Score: 54/100  ██████████░░░░░░░░░░

📋 Recommended Plans

★ Plan A — Recommended — Simplest Path   Score: 89/100
  1. Swap 240.00 PHRS → USDT via Pharos Port Swap
  2. Hold 304 USDT total
  Expected outcome : ~304 USDT (target: 500) ⚠ partial
  APY              : 0%
  Risk after       : Low (34/100)
  Score            : 89/100  ██████████████████░░

  Plan B — Alternative — Keep PHRS + Borrow   Score: 61/100
  1. Deposit 128.00 PHRS as collateral on FaroSwap
  2. Swap 64.00 PHRS → USDT for liquidity
  Expected outcome : ~262 USDT + LP position
  APY              : 4.5%
  Risk after       : High (64/100)
  Score            : 61/100  ████████████░░░░░░░░
```

### Scenario 2: "Reduce my portfolio risk"

```
🎯 Goal Detected
  Risk Reduction [medium risk]

📋 Recommended Plans

★ Plan A — Recommended — Partial De-risk   Score: 91/100
  1. Swap 128.00 PHRS → USDT (40% of volatile)
  Expected outcome : Risk score: 54 → 24
  Risk after       : Low (24/100)
  Score            : 91/100  ██████████████████░░
```

### Scenario 3: "Earn yield with low risk"

```
🎯 Goal Detected
  Yield Generation [low risk]

📋 Recommended Plans

★ Plan A — Conservative — Harbor Vault   Score: 83/100
  1. Deposit 256.00 PHRS into Pharos Harbor vault
  Expected outcome : ~9.5% APY on PHRS holdings
  APY              : 9.5%
  Risk after       : Low (34/100)
  Score            : 83/100  ████████████████░░░░

  Plan B — Balanced — FaroSwap LP   Score: 67/100
  1. Swap 128.00 PHRS → USDT (50/50 prep)
  2. Add PHRS/USDT liquidity to FaroSwap pool
  Expected outcome : ~14.2% APY (LP fees + rewards)
  APY              : 14.2%
  Risk after       : Medium (59/100)
  Score            : 67/100  █████████████░░░░░░░
  ⚠  Impermanent loss risk if PHRS price moves significantly
```

---

## JSON Output Mode

```bash
python src/goalpilot.py \
  --wallet 0xDEMO \
  --goal "earn yield with low risk" \
  --dry-run \
  --json
```

Output:
```json
{
  "goal": {
    "goal_type": "yield",
    "risk_preference": "low",
    ...
  },
  "wallet": {
    "native_PHRS": 320.0,
    "total_USD": 391.4,
    "risk_score": 54
  },
  "plans": [
    {
      "plan_id": "A",
      "label": "Conservative — Harbor Vault",
      "score": 83,
      "expected_apy": 9.5,
      "risk_after": 34,
      "steps": [...]
    }
  ]
}
```

---

## Live Wallet Mode

```bash
# Atlantic testnet
python src/goalpilot.py \
  --wallet 0xYourRealAddress \
  --network atlantic-testnet \
  --goal "earn yield with low risk"

# Mainnet (read-only — no transactions sent)
python src/goalpilot.py \
  --wallet 0xYourRealAddress \
  --goal "reduce my portfolio risk"
```

---

## Interactive REPL

```bash
python src/goalpilot.py --wallet 0xYourAddress
# GoalPilot> I want 500 USDT by tomorrow
# GoalPilot> reduce my risk
# GoalPilot> quit
```
