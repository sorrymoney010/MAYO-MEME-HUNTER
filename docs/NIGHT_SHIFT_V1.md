# MAYO NIGHT SHIFT V1

## Scope
Read-only Solana research orchestration. No wallet connection, signing, transaction preparation, order submission, or profit claims. Seven deterministic software roles share evidence and persist observations in SQLite. They are not independent LLM agents.

## Seven roles
1. Desk Lead — validates candidate identity and source handoff.
2. Launch Hunter — records discovery source and launch metadata; unknown times remain unknown.
3. Developer Investigator — requires attributable creator/linked-wallet evidence.
4. Bundle Detective — requires launch-block or early-wallet concentration evidence.
5. Market Analyst — relays observed price, liquidity, volume and transaction metrics.
6. Strategy Agent — permits paper review only when required evidence exists; creates no order signal.
7. Risk & Execution Controller — enforces the paper-only boundary and fail-closed decisions.

## Data limitations
The current DEX Screener adapter is a public profile/pair discovery feed, not a complete Pump.fun launch feed. It does not establish creator ownership, related-wallet attribution, launch bundle activity, complete deployer history, Token-2022 extension safety, or executable sellability. Those fields remain UNKNOWN. PumpPortal's launch/migration collector is not yet merged into a unified enrichment pipeline.

## Install and run
Install the project with pip editable mode, then run:
- One scan: mayo-night-shift --once --timezone America/Chicago
- Recurring scan and local 07:00 report: mayo-night-shift --timezone America/Chicago --interval 600 --morning-hour 7
- Report from saved UTC observations: mayo-night-shift --db data/night_shift.sqlite3 --report-since 2026-11-18T00:00:00+00:00

The scheduler is a foreground process. It stops when the host sleeps, shuts down, or the process exits. Ctrl-C stops it. The database defaults to data/night_shift.sqlite3.

## Output and safety
Each candidate receives seven role records and PASS_FOR_PAPER_REVIEW or SKIP. A pass is not a trade recommendation or fill. V1 does not open paper positions or calculate P&L; the morning report reports P&L as null. No live trading command exists.

Before later phases implement: PumpPortal-to-enrichment pipeline; attributable holder aggregation; Token-2022 extension parsing; launch-block bundle heuristics; verified deployer history; quote-based sellability at defined size/price impact; durable paper portfolio/fill model; scheduler supervision and notification delivery. Every security field needs source URLs, timestamps and provenance.
