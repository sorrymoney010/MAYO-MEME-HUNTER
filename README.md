# MAYO MEME HUNTER — Snag & Go

Independent Solana meme-token discovery and paper-trading research engine.

> **Paper-only.** No wallet signer, transaction submission, order placement, or transfer capability exists in this project. V2 live-data collection is read-only.

Independent of [Mayo Kraken Trader](https://github.com/sorrymoney010/mayo-bot).

## V1 + V2 capabilities

- Read-only DEX Screener token/pair discovery.
- **V2 PumpPortal WebSocket collector:** one reconnecting connection, free new-token and migration subscriptions, append-only JSONL events. Metered trade/account streams are disabled by default.
- **V2 Solana RPC mint inspection:** parsed mint/freeze authorities, token program owner, supply, largest token accounts and a clearly labeled top-account concentration estimate.
- Unknown security facts block candidate qualification.
- Fee-aware paper replay, risk controls, wallet-history research and offline HTML dashboard.
- Offline tests and GitHub Actions CI.

The PumpPortal collector follows the documented free `subscribeNewToken` and `subscribeMigration` methods. Token/account trade streams are metered at 0.01 SOL per 10,000 events and are not enabled by this build. See [official API docs](https://pumpportal.fun/data-api/real-time/) and [fees](https://pumpportal.fun/fees/).

## Install and test (Python 3.10+)

```bash
git clone https://github.com/sorrymoney010/MAYO-MEME-HUNTER.git
cd MAYO-MEME-HUNTER
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## V2 commands

Collect real launch and migration events (no trade stream, no wallet needed):
```bash
mayo-meme stream --out data/solana_events.jsonl
```
Stop with Ctrl-C. For a bounded smoke run use `--seconds 60`.

Inspect a mint through read-only Solana RPC:
```bash
mayo-meme inspect-mint --mint YOUR_TOKEN_MINT
``
Optional: set `SOLANA_RPC_URL` to your own RPC endpoint. The public default may rate-limit.

Run existing paper replay and dashboard:
```bash
mayo-meme replay --file examples/sample_snapshots.jsonl --out results/demo.json
mayo-meme dashboard --file results/demo.json --out results/dashboard.html
mayo-meme scan --limit 10 --out results/watchlist.json
```

## Important safety and data limitations

- The collector records creation and migration events; it does not yet produce complete market snapshots, unique buyer counts or reliable 5-minute volume.
- PumpPortal trade/account subscriptions are intentionally disabled because they incur metered fees and require an API key plus linked funded wallet. Do not enable without explicit cost review.
- Mint inspection is partial. Token-2022 extensions remain UNKNOWN; top-10 concentration is token-account based, not deduplicated by owner; creator concentration and sell-route availability are not verified.
- A revoked mint authority does not prove a token is safe. Quotes can fail and tokens can become unsellable.
- No real trading, wallet connection, key handling or automated spending. Do not add these without a separate security review and explicit owner approval.

## Next V2 work

Persisted event deduplication, PumpSwap/DEX price snapshots, parsed Token-2022 extension inspection, owner-aggregated holder analysis, sell-quote checks, and a live read-only candidate board. See [BUILD_HANDOFF.md](BUILD_HANDOFF.md).
