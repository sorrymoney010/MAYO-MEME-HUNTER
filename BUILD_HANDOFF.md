# MAYO MEME HUNTER — Engineering handoff

## Project ownership and separation

Official standalone repository: https://github.com/sorrymoney010/MAYO-MEME-HUNTER

Separate from the Kraken trader at https://github.com/sorrymoney010/mayo-bot. Do not merge into it, alter its configuration, or unlock live trading there.

## V1 scope

Python standard-library runtime, Python >=3.10. CLI:
- `mayo-meme scan`: read-only public DEX Screener profiles and pairs; every result WATCH_ONLY_UNVERIFIED.
- `mayo-meme replay`: fee-aware next-observation paper engine; reject unknown token security; stop/target/trailing/time exits; max daily loss and drawdown; simulated realized P&L and decisions.
- `mayo-meme wallets`: offline realized FIFO wallet analysis after assumed copy friction.
- `mayo-meme dashboard`: static HTML from the paper report.

14 offline unit tests run on the bundled synthetic fixtures. No authenticated Solana RPC checks, network scans, profit evidence, or live orders have been verified for V1.

## Proposed implementation sequence

### V2a — Reliable events
- Add normalized event schema: provider, observed_at, event timestamp, slot, mint, pool, market, price units, unique event id.
- Ingest Pump.fun new-mint, PumpSwap migration and DEX market events, with separate population labels; do not treat a profile endpoint as an exhaustive launch stream.
- Implement de-duplication, backoff, bounded queues, source-age thresholds, rate telemetry, reconnection, persisted raw events and replay. Use SQLite first.
- Ensure no paid provider or fee-bearing subscription starts without explicit cost approval.

### V2b — Safety and sellability
- Integrate Solana RPC mint authority and freeze authority queries. Handle Token-2022 extensions and transfer restrictions explicitly.
- Normalize token accounts to wallet owners, check holder concentration, creator exposure and suspicious funding clusters.
- Validate actual pool liquidity/price impact and obtain a size-specific executable-looking **sell quote**. Quotes can still fail; store freshness and sources.
- Security status must be VERIFIED, FAILED or UNKNOWN; UNKNOWN blocks an entry. Explicitly distinguish unverifiable from definitely malicious.

### V2c — Strategy evaluation
- Keep post-launch/pre-migration and post-migration universes separate.
- Test Snag & Go momentum confirmation, breakout continuation, and wallet-following alerts as different strategies.
- Use recorded events with accurate observation/execution lag; model spreads, fees, priority fees, failed exits, adverse selection, partial fills, feed gaps and selection bias.
- OOS and rolling walk-forward evaluation; include rugged and delisted tokens. Report confidence ranges, trade count and worst drawdowns—not just win rate.
- Pre-live research screen: >=30 independent OOS trades, net profit factor >=1.10, majority positive OOS folds, tolerable drawdown and >=7-day stable monitoring. These are minimum screens, not sufficient standalone proof.

### V3 — Monitoring
- Provide read-only mobile dashboard with candidate board, why rejected, provider freshness, event gaps, paper positions, P&L, risk status, simulated fills and source provenance.
- Optional alerts for monitored candidates, clearly labeled WATCH-ONLY/PAPER and including contract address and data age.
- Immutable-ish append-only audit decisions, replayable across restarts.

### V4 — Only after separate owner approval
- Propose a separate executor with signer isolation, no withdrawal capability, capped hot-wallet funds, explicit spend/fee ceilings, idempotent intents, transaction simulation and on-chain confirmation.
- Emergency pause, reconciliation, stale-quote veto, and documented loss-of-connectivity procedure.
- Never turn it on by default, never assume user consent to real orders or provider charges.

## Acceptance tests next

1. 14 offline V1 tests remain green.
2. No public profile lacking security proof can produce executable order intent.
3. Duplicate, delayed or stale events do not duplicate simulated trades.
4. Blocked sell routes do not become fabricated gains.
5. Portfolio entry limits don't prevent safe exits.
6. Source failures and restart recovery don't corrupt P&L.
7. Credentials never enter source, logs or GitHub.
