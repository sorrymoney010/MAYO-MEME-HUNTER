# MAYO MEME HUNTER — build handoff

Independent Solana meme-token discovery and trading agent. Proposed owner wallet: a dedicated Phantom account. No Kraken/Binance dependencies.

## Current status
- V1/V2 read-only discovery, launch/migration stream, mint inspector, paper engine and dashboard.
- Jupiter Swap API V2 quote-preparation scaffold.
- Phantom signing design: PHANTOM_SIGNING.md.
- Real transaction submission is hard-disabled. No signer is implemented.
- User explicitly requested: use Phantom as proposed wallet, design isolated signing and autonomous trading safeguards, do not enable real trades.

## Phantom design
Default first phase: separate MAYO Phantom account; owner reviews every transaction; agent never receives seed phrase/private key.
Phantom Auto-Confirm is documented only for supported apps. It allows up to 10 transactions/minute for two hours, can stop on suspicious activity, and can be revoked. MAYO must not assume it is eligible; if not shown in Phantom, manual review only.
For true 24/7 automation, only consider a separate low-balance KMS/HSM/MPC signer with narrow swap-only policy after explicit owner approval. Phantom remains the owner-facing oversight wallet. No secret export/import into the agent.

## Initial code ceilings (not activated)
0.05 SOL per buy, 0.20 SOL daily purchases, 5% max price impact, 10-second signal freshness, 2 open positions. Add max total exposure and daily realized+unrealized loss stop before live mode.

## Required before live trading
1. Complete market data and security gates: Token-2022 extensions, owner-aggregated holder analysis, creator/funder links, reliable liquidity/volume, size-specific sell route.
2. Transaction decoder/allowlist: exact programs, accounts, mints, input/output amounts, minimum output, fees, expiry; reject arbitrary transfers, approvals, authority changes, unknown instructions.
3. Isolated signer with no key export and no withdrawal permission, if Phantom-supported connection cannot support desired autonomy.
4. Durable SQLite/Postgres ledger with atomic spend reservation, idempotency, restart-safe daily limits and position state.
5. Position watcher and automatic sell path; partial fills, failed sells, retry ceilings, reconciliation.
6. Circuit breakers, loss stop, kill switch, owner alerts, signer revocation.
7. Devnet and failure-injection tests, real-market paper run, independent security review, explicit owner authorization.

No funding instructions or live activation until the owner approves a final custody model and limits.
