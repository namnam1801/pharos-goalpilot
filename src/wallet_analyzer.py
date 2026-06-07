"""
wallet_analyzer.py — Wallet State Analyzer
Pharos GoalPilot v1.0.0

Fetches native balance + ERC-20 holdings via JSON-RPC.
Read-only. No private key required.
"""

import json
import requests
from dataclasses import dataclass, field
from typing import Dict, Optional

# ── Known ERC-20 tokens on Pharos ────────────────────────────────────────────

KNOWN_TOKENS = {
    "mainnet": {
        "USDT": "0x817e08bC3f4E0a48aB286d60dc64Cb4E68E9F19F",
        "USDC": "0x00000000000000000000000000000000000000000",  # placeholder
        "PROS": "0x00000000000000000000000000000000000000001",  # placeholder
    },
    "atlantic-testnet": {
        "USDT": "0x51fE9ebc88B66FB29038B487F4dA576c6d081a5E",
        "USDC": "0x00000000000000000000000000000000000000000",
        "PROS": "0x00000000000000000000000000000000000000001",
    },
}

ERC20_DECIMALS = {"USDT": 6, "USDC": 6, "PROS": 18, "WETH": 18}

ERC20_BALANCE_OF_SELECTOR = "0x70a08231"  # balanceOf(address)

# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class TokenBalance:
    symbol: str
    amount: float
    usd_value: float
    is_stablecoin: bool
    is_idle: bool           # true if not staked/deposited anywhere


@dataclass
class WalletSnapshot:
    address: str
    network: str
    native_phrs: float
    native_usd: float
    tokens: Dict[str, TokenBalance] = field(default_factory=dict)
    total_usd: float = 0.0
    stablecoin_usd: float = 0.0
    volatile_usd: float = 0.0
    idle_usd: float = 0.0
    risk_score: int = 50    # 0 = all stable, 100 = all volatile
    error: Optional[str] = None

    def summary(self) -> dict:
        return {
            "address": self.address,
            "native_PHRS": round(self.native_phrs, 4),
            "native_USD": round(self.native_usd, 2),
            "tokens": {s: {"amount": round(b.amount, 4), "usd": round(b.usd_value, 2)}
                       for s, b in self.tokens.items()},
            "total_USD": round(self.total_usd, 2),
            "stablecoin_USD": round(self.stablecoin_usd, 2),
            "volatile_USD": round(self.volatile_usd, 2),
            "idle_USD": round(self.idle_usd, 2),
            "risk_score": self.risk_score,
        }


# ── RPC helpers ───────────────────────────────────────────────────────────────

def _rpc(rpc_url: str, method: str, params: list) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        r = requests.post(rpc_url, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _get_native_balance(rpc_url: str, address: str) -> Optional[int]:
    """Returns balance in wei."""
    resp = _rpc(rpc_url, "eth_getBalance", [address, "latest"])
    if "result" in resp:
        return int(resp["result"], 16)
    return None


def _get_erc20_balance(rpc_url: str, token_address: str, wallet_address: str) -> Optional[int]:
    """Returns raw token balance (needs decimals to convert)."""
    # Pad wallet address to 32 bytes for ABI encoding
    padded = wallet_address.lower().replace("0x", "").zfill(64)
    data = ERC20_BALANCE_OF_SELECTOR + padded
    resp = _rpc(rpc_url, "eth_call", [
        {"to": token_address, "data": data}, "latest"
    ])
    if "result" in resp and resp["result"] and resp["result"] != "0x":
        try:
            return int(resp["result"], 16)
        except ValueError:
            return None
    return None


# ── Price feed (static fallback, can be replaced with oracle) ─────────────────

def _load_prices(assets_dir: str = "assets") -> Dict[str, float]:
    try:
        with open(f"{assets_dir}/protocols.json") as f:
            data = json.load(f)
            return data.get("token_prices_usd", {})
    except Exception:
        return {"PHRS": 0.52, "PROS": 0.18, "USDT": 1.0, "USDC": 1.0, "WETH": 2610.0}


# ── Risk scorer ───────────────────────────────────────────────────────────────

def _compute_risk_score(stable_usd: float, volatile_usd: float) -> int:
    """
    Risk score 0–100.
    0 = 100% stablecoins, 100 = 100% volatile.
    """
    total = stable_usd + volatile_usd
    if total == 0:
        return 50
    volatile_ratio = volatile_usd / total
    return min(100, int(volatile_ratio * 100))


# ── Main analyzer ─────────────────────────────────────────────────────────────

def analyze_wallet(
    address: str,
    network: str = "mainnet",
    rpc_url: Optional[str] = None,
    assets_dir: str = "assets",
) -> WalletSnapshot:
    """
    Fetch wallet state from Pharos RPC and return a WalletSnapshot.

    Args:
        address:   Wallet address (0x...)
        network:   "mainnet" or "atlantic-testnet"
        rpc_url:   Override RPC URL (optional)
        assets_dir: Path to assets/ folder for prices and config

    Returns:
        WalletSnapshot with all balances and computed metrics
    """
    # Load network config
    try:
        with open(f"{assets_dir}/networks.json") as f:
            net_cfg = json.load(f)["networks"][network]
    except Exception:
        net_cfg = {
            "rpc": "https://rpc.pharos.xyz" if network == "mainnet"
                   else "https://atlantic.dplabs-internal.com"
        }

    rpc = rpc_url or net_cfg["rpc"]
    prices = _load_prices(assets_dir)
    phrs_price = prices.get("PHRS", 0.52)
    snapshot = WalletSnapshot(address=address, network=network,
                               native_phrs=0.0, native_usd=0.0)

    # ── Native PHRS balance ──
    native_wei = _get_native_balance(rpc, address)
    if native_wei is None:
        snapshot.error = "Could not fetch native balance. Check RPC or address."
        return snapshot

    snapshot.native_phrs = native_wei / 1e18
    snapshot.native_usd = snapshot.native_phrs * phrs_price

    # ── ERC-20 balances ──
    token_contracts = KNOWN_TOKENS.get(network, {})
    stablecoins = {"USDT", "USDC"}

    for symbol, contract in token_contracts.items():
        if contract.startswith("0x000000000000000000000000000000000000000"):
            continue  # placeholder — skip
        decimals = ERC20_DECIMALS.get(symbol, 18)
        raw = _get_erc20_balance(rpc, contract, address)
        if raw is None or raw == 0:
            continue
        amount = raw / (10 ** decimals)
        usd = amount * prices.get(symbol, 0.0)
        snapshot.tokens[symbol] = TokenBalance(
            symbol=symbol,
            amount=amount,
            usd_value=usd,
            is_stablecoin=(symbol in stablecoins),
            is_idle=True,  # assume idle — LP detection TBD
        )

    # ── Aggregate metrics ──
    all_usd = snapshot.native_usd
    stable_usd = 0.0
    volatile_usd = snapshot.native_usd  # PHRS is volatile

    for tb in snapshot.tokens.values():
        all_usd += tb.usd_value
        if tb.is_stablecoin:
            stable_usd += tb.usd_value
        else:
            volatile_usd += tb.usd_value

    idle_usd = sum(tb.usd_value for tb in snapshot.tokens.values() if tb.is_idle)
    idle_usd += snapshot.native_usd  # native PHRS treated as idle if not staked

    snapshot.total_usd = all_usd
    snapshot.stablecoin_usd = stable_usd
    snapshot.volatile_usd = volatile_usd
    snapshot.idle_usd = idle_usd
    snapshot.risk_score = _compute_risk_score(stable_usd, volatile_usd)

    return snapshot


# ── Demo mode (no real wallet needed) ────────────────────────────────────────

def mock_wallet(address: str = "0xDEMO") -> WalletSnapshot:
    """Return a realistic mock wallet for demo/dry-run purposes."""
    snapshot = WalletSnapshot(
        address=address,
        network="atlantic-testnet",
        native_phrs=320.0,
        native_usd=166.4,
    )
    snapshot.tokens = {
        "USDT": TokenBalance("USDT", 180.0, 180.0, True, True),
        "PROS": TokenBalance("PROS",  250.0, 45.0, False, True),
    }
    snapshot.total_usd = 166.4 + 180.0 + 45.0   # 391.4
    snapshot.stablecoin_usd = 180.0
    snapshot.volatile_usd = 166.4 + 45.0          # 211.4
    snapshot.idle_usd = 391.4                      # everything idle in demo
    snapshot.risk_score = _compute_risk_score(180.0, 211.4)  # ~54
    return snapshot


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    addr = sys.argv[1] if len(sys.argv) > 1 else None

    if addr:
        print(f"Fetching wallet: {addr}")
        snap = analyze_wallet(addr, network="atlantic-testnet")
    else:
        print("No address provided — using mock wallet")
        snap = mock_wallet()

    if snap.error:
        print(f"Error: {snap.error}")
    else:
        import json as _json
        print(_json.dumps(snap.summary(), indent=2))
