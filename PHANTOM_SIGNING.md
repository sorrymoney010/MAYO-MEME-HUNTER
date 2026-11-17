# Phantom wallet and isolated signing design

Status: DESIGN APPROVED / IMPLEMENTATION NOT ENABLED. No real trades, signatures, or transaction submissions are allowed by this build.

## Wallet role

Use Phantom as the owner's Solana wallet interface and authorization surface. Create a **new dedicated MAYO account** inside Phantom; do not connect the account that holds long-term savings or unrelated assets. Fund it only with an amount the owner can afford to lose. Keep the recovery phrase offline and never send it to MAYO, GitHub, a server, a bot operator, or ChatGPT.

Phantom is self-custodial. Its current terms describe supported connections for AI agents, but put responsibility for an agent's activity and permission scope on the wallet owner. MAYO must only use Phantom's documented/supported connection path; never simulate a human, scrape the wallet UI, export keys, or store a recovery phrase.

## Signing modes

### Mode A — review every transaction (default)
1. MAYO builds a candidate decision and obtains a fresh Jupiter Swap API V2 order.
2. A policy service decodes the unsigned transaction and checks every instruction, program ID, source/destination account, mint, SOL/token amount, fee, slippage and expiry.
3. A user-facing dApp requests signing through the official Phantom connection/provider.
4. Phantom displays the transaction for owner review. Reject unexpected instructions or warnings.
5. Only after the owner signs may the signed order be sent to Jupiter `/execute`; reconcile the confirmed signature and actual token/SOL deltas.

This mode is interactive, not unattended automation.

### Mode B — Phantom Auto-Confirm (future, only if Phantom supports MAYO)
Phantom documents Auto-Confirm for certain supported connected apps, including Jupiter. It is not automatically available to every app. The owner must see MAYO listed as a supported app and deliberately enable Auto-Confirm in Phantom. Phantom's current help says Auto-Confirm is limited to up to 10 transactions per minute for two hours; suspicious activity can stop it. The owner can revoke permission in Connected Apps or end all Auto-Confirm sessions.

Do not infer MAYO qualifies. Do not bypass the supported-app list, prompt approvals, or duration. If the toggle is unavailable, stay in Mode A. Even if enabled, MAYO's stricter limits apply. This session limit is not an unlimited unattended mandate.

### Mode C — isolated managed signer (alternative only after owner review)
If true 24/7 autonomous execution is required and Phantom's supported agent connection cannot provide scoped authorization, use a separate low-balance Solana hot wallet held by a dedicated KMS/HSM/MPC signer. Keep the Phantom owner wallet as funding/oversight wallet, not as a key file copied to the bot. The signer must expose only an allowlisted swap-signing operation, never raw-key export or arbitrary message signing. This is a separate custody decision and requires explicit owner approval; it is not selected or provisioned here.

## Mandatory policy controls
- Main/long-term Phantom account is never the bot's trading account.
- Separate dedicated account and strict low balance; no withdrawal or arbitrary transfer permission.
- Per-buy and daily spend caps, maximum total exposure, maximum open positions, max daily realized+unrealized loss, and hard global kill switch.
- Allowlist only exact swap program/router instruction set. Reject unknown programs, token approvals, delegate changes, authority changes, account closes, transfers to arbitrary recipients, durable nonce changes and unexpected fee payers.
- Validate exact input/output mints, wallet owner, amounts, minimum output, slippage, priority fees, platform fees, route, destination accounts, quote age and transaction expiry.
- Re-fetch quote immediately before signing; stale quotes or blockhash/expiry mismatch fail closed.
- Token safety gates must include Token-2022 extensions, owner-aggregated concentration, creator/deployer links, liquidity quality, holder distribution and size-specific sell-route checks. Unknown means no trade.
- One trade intent gets one idempotency key. Reserve spend atomically before signing to prevent concurrent workers overspending.
- Verify on-chain finality and actual balance changes; never infer success from HTTP acceptance alone.
- Persist append-only decisions, approvals, quotes, transaction hashes, confirmations, fills, fees and P&L. Redact secrets.
- Circuit breakers: stale/missing feed, RPC disagreement, repeated failures, abnormal slippage, daily loss limit, balance mismatch, signer error, or suspicious transaction -> stop all new buys and alert owner.
- No automatic deposits, withdrawals, transfers between wallets, seed phrase export, or arbitrary token approvals.
- Require simulation, devnet tests, paper trading on real captured events, independent transaction-parser review and owner sign-off before any live mode exists.

## Proposed initial guardrails (not activated)
The current code ceilings remain: max 0.05 SOL per buy, max 0.20 SOL daily purchases, max 5% quoted price impact, max 10-second signal age and 2 open positions. These are maximum code ceilings, not suggested funding or a guarantee against loss. Add a separate daily-loss stop and total exposure limit before live implementation.

## Kill switch and revocation
- MAYO local kill switch stops new orders immediately and cancels pending unsigned intents.
- Phantom owner can disconnect MAYO or revoke Auto-Confirm in Connected Apps.
- Treat revocation as eventually effective: stop dispatch immediately, reject new signatures, and monitor already-broadcast transactions until finality.
- On suspected compromise: stop the agent, revoke app permissions, move remaining funds to a fresh secure wallet if appropriate, and investigate transaction signatures.

## Official references
- Phantom terms (AI-agent access, responsibilities and risks): https://phantom.com/terms
- Phantom Auto-Confirm instructions and limits: https://help.phantom.com/articles/19385761078547
- Phantom wallet security: https://help.phantom.com/articles/how-to-keep-your-phantom-wallet-secure-13515761228051
- Phantom KMS: https://help.phantom.com/articles/50639521822227
- Solana production signing guidance: https://solana.com/docs/core/transactions/signing-in-production
- Jupiter Swap API V2: https://developers.jup.ag/docs/swap
- Jupiter order and execute: https://developers.jup.ag/docs/swap/order-and-execute
