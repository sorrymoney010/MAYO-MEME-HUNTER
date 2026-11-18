# Adaptive Research Engine V1

## Purpose
Build a durable evidence base for MAYO MEME HUNTER. This phase is research-only: no wallet connection, key access, quote generation, transaction construction, signing, or submission.

## Data flow
1. Capture PumpPortal create/migration events with `mayo-meme stream --out data/solana_events.jsonl`.
2. Run the built-in DEX Screener polling adapter against the collected launch list:
   `mayo-meme collect-snapshots --events data/solana_events.jsonl --out data/market_snapshots.jsonl --interval 300 --max-tokens 20`
   Stop it with Ctrl-C. Use `--seconds 3600` for a bounded one-hour run. It polls at most 30 recent mints and defaults to one request per mint every five minutes.
3. The collector writes timestamped price, liquidity, 5-minute volume, buys/sells, and pool provenance. Unique buyers and holder/creator concentration remain unknown, not inferred. A manual/replay source can also be used. Each JSONL row needs `mint`, `ts` (Unix epoch seconds or ISO-8601), and positive `price_usd`. Optional features include liquidity, 5-minute volume, buys/sells, unique buyers, top-10/creator percentages, and 5-minute price change.
4. Import events and snapshots:
   `mayo-meme research ingest --events data/solana_events.jsonl --snapshots data/market_snapshots.jsonl`
5. Build forward labels:
   `mayo-meme research label --max-lag-seconds 180`
6. Review data coverage and outcome summaries:
   `mayo-meme research report`
7. Compare predeclared baseline rules:
   `mayo-meme research study --horizon 5`

The default database is `data/research.sqlite3`. Use `--db PATH` on each research command to select another database.

## Label methodology
The entry is the first recorded snapshot at or after a launch event. For each horizon (1, 5, 10, 15, 30, 60 minutes), the exit is the first recorded snapshot at or after entry plus the horizon, within the configured maximum lag. By default, the first market snapshot must arrive within 120 seconds of the launch event (`--max-entry-delay-seconds`); otherwise all horizons for that event are marked incomplete. The label stores entry/exit timestamps and prices, forward return, maximum run-up, maximum drawdown, and event-to-entry capture delay. Snapshots before the event are excluded. Missing horizon observations are incomplete, not zero-return outcomes.

## Experiments
V1 compares three predeclared cohorts: all labeled events, liquidity/volume floor, and buy-pressure/momentum. It reports sample size, mean/median return, positive rate, and mean maximum drawdown. Fewer than 30 samples is marked insufficient. These are descriptive research comparisons, not profitable strategy claims.

## Correctness and research controls
- Raw payloads are retained alongside normalized fields.
- Event and snapshot ingestion is idempotent for stable provider/signature/time keys.
- Timestamps are normalized to UTC epoch seconds.
- Labels use only post-event observations; no future data enters the feature row.
- No missing observation is silently converted to zero.
- Results must be split chronologically into discovery, validation, and untouched holdout periods before strategy selection.
- Avoid survivorship bias: preserve failed launches and delisted/rugged tokens.
- Add provenance, source health, clock skew, missingness, and collection coverage before treating outcomes as representative.
- Include fees, slippage, failed sells, and executable-size liquidity before evaluating paper expectancy. V1 labels are mark-price research, not executable fills.

## V1 limitations
The PumpPortal collector captures create/migration events, and the DEX Screener adapter now polls recent event mints for market snapshots. It is a bounded watchlist collector, not a guaranteed complete market tape: it can miss launches outside the recent-mint cap, pools with no DEX pair yet, short-lived price moves between polls, and data during downtime. A durable supervisor, gap/coverage monitor, and richer provenance checks are required before meaningful learning curves or strategy claims can be produced. Wallet clustering, developer-history attribution, Token-2022 extension analysis, and bundle detection remain separate future research adapters.

All outputs include `execution_enabled: false`. MAYO MEME HUNTER remains isolated from Mayo Kraken Trader.
