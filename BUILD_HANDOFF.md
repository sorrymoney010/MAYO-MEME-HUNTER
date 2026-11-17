# MAYO MEME HUNTER — execution handoff

## Product definition
Standalone Solana meme-coin trading agent. Keep discovery, risk, wallet, execution, accounting and monitoring inside this repository. Do not add dependencies on unrelated bots, brokers or exchanges.

## Target behavior
Autonomous discovery -> screening -> buy -> position monitoring -> sell -> reconciliation, within owner-authorized limits. Live execution stays disabled until all safety gates pass and owner explicitly activates it.

## Current scaffold
\`src/mayo_meme_hunter/execution.py\` provides Jupiter Swap API V2 /order and /execute calls, candidate/security/sellability gates, freshness checks, and spend/position ceilings. Hard code ceilings: 0.05 SOL per buy; 0.20 SOL daily buys; 5% price impact; 10-second signal age; two open positions. \`MAYO_LIVE_TRADING_ENABLED\` defaults false. No signer or private-key handling exists.

## Required before live autonomous trading
1. Isolated signer/hardware-wallet service. Decode and validate every transaction instruction, mint, amount, wallet, fee and expiry before signing. No seed phrase in this repo.
2. Persistent ledger and atomic spend reservations; restart-safe daily limits.
3. Wallet token-balance and position monitor plus reliable price feed.
4. Automatic sell quote/order path, partial-fill handling, retry limits and stuck-position alerts.
5. Daily realized+unrealized loss cap, exposure limits, kill switch and stale-feed veto.
6. Devnet transaction tests, real-market paper testing and independent security review.
7. Owner explicitly chooses custody model, funding amount and risk settings.

Jupiter docs: https://developers.jup.ag/docs/swap and https://developers.jup.ag/docs/swap/order-and-execute
