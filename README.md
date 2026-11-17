# MAYO MEME HUNTER — Snag & Go

**An independent Solana meme-token discovery, safety-screening and paper-trading research engine.**

> **V1 is NOT a live sniper.** It cannot sign transactions, access a wallet, transfer money, or submit real orders. Its real-data adapter is read-only. No profit claims are made.

This repository is independent from [Mayo Kraken Trader](https://github.com/sorrymoney010/mayo-bot). The Kraken bot has not been changed.

## Current V1 features

- **Discover (read-only)** — inspect recently profiled Solana tokens and pairs with the public DEX Screener API.
- **Reject unsafe or unverified tokens** — missing mint/freeze authority, holder concentration, token-program safety and sellability evidence block entries.
- **Research scoring** — 0–100 heuristic score using liquidity, 5-minute volume, buy pressure, unique buyers, holder distribution and momentum. **Not** a probability of success.
- **Fee-aware paper replay** — signal on one observation, enter on the next, account for assumed fees, slippage and network costs.
- **Snag & Go risk rules** — stops, take profit, trailing exits, max hold time, daily loss halt, max drawdown, allocation limits, position count and cooldown.
- **Smart wallet research** — FIFO realized P&L with a configurable copy-trading friction assumption; no wallet keys or live copying.
- **Static HTML dashboard** — offline simulated account and decision report.
- **Tests** — 14 offline unit tests in `tests/test_core.py`; GitHub Actions workflow included.

## Quick start (Python 3.10+)

```bash
git clone https://github.com/sorrymoney010/MAYO-MEME-HUNTER.git
cd MAYO-MEME-HUNTER
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v

# Entirely synthetic fixtures; no network or funds
mayo-meme replay --file examples/sample_snapshots.jsonl --out results/demo.json
mayo-meme wallets --file examples/sample_wallet_events.jsonl
mayo-meme dashboard --file results/demo.json --out results/dashboard.html

# Optional public-data discovery (network required, no orders)
mayo-meme scan --limit 10 --out results/watchlist.json
```

## What happens when you scan

The public DEX Screener adapter can identify token pairs, age, prices, liquidity and trading activity, but it **does not verify** token mint/freeze authority, Token-2022 restrictions, owner clustering, holder distribution, unique buyers or actual sell-route feasibility. Every row is marked `WATCH_ONLY_UNVERIFIED`, and missing security facts block trading decisions.

It is not a comprehensive real-time Pump.fun mint or migration feed.

## V1 strategy hypotheses

Two research strategies will be evaluated after real data capture:

1. **Snag & Go:** enter after verified post-launch/post-migration momentum and exit on stop, target, trailing signal or 15-minute timer.
2. **Momentum Rider:** hold a verified breakout longer with trailing exits (planned, not implemented).
3. **Wallet Watch:** analyze whether observed winning wallets can be followed *profitably after latency and costs* (offline research implemented; automatic monitoring planned).

**Starting paper parameters:** $100 synthetic starting cash; minimum score 70; $25,000 liquidity; $10,000 5-minute volume; 20 unique buyers; 1% equity risk per stop; 10% max allocation; 2 positions; 3% daily-loss stop; 10% maximum drawdown; -12% price stop; +25% target; trailing exit after +15% gain; 15-minute holding limit. These are configurable *research hypotheses*, not proven optimal settings.

The replay assumes 50 bps trading fees and 150 bps slippage **on each side**, plus $0.02 network costs per side. Actual prices, liquidity, priority fees and unsellable positions can be much worse.

## Evidence and limits

Synthetic example wins only confirm that the program runs; they are not real trades, actual performance or evidence of a repeatable edge. The V1 discovery API has incomplete security coverage, so public observations cannot currently qualify for paper BUY signals.

Before considering live trading: capture actual events including failed tokens, replay with accurate latency and costs, run out-of-sample and walk-forward tests, verify actual sell routes and contracts, examine drawdowns and source outages, and require a separate safety review and fresh owner authorization. A minimum 30-trade / profit-factor 1.10 screen is **not** proof of profitability.

## What's next

See [BUILD_HANDOFF.md](BUILD_HANDOFF.md): realtime Solana event ingestion → on-chain security checks → verified sell quotes → event store → paper alerts/observability → realistic out-of-sample research. Live execution is **not** included or approved.

## Public references

- [DEX Screener API](https://docs.dexscreener.com/api/reference)
- [PumpPortal data stream](https://pumpportal.fun/data-api/real-time/)
- [Jupiter developer docs](https://dev.jup.ag/)
- [Solana developer docs](https://solana.com/docs)

**Security:** Never paste seed phrases, private keys or signing credentials into issues, chat, or source code. See [SECURITY.md](SECURITY.md).
