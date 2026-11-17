# Security policy — MAYO MEME HUNTER

Use a dedicated Phantom account for MAYO; never connect the owner's long-term holdings account. Never request, store, transmit or commit a recovery phrase, private key, PIN or authenticator secret.

Live transaction signing and submission are hard-disabled in the current build. A future integration must use Phantom's supported connection/agent mechanisms or a separately approved isolated KMS/HSM/MPC signer. Do not scrape wallet UI, impersonate user clicks, bypass Auto-Confirm eligibility, or export Phantom keys.

Allowlist exact swap instructions and reject arbitrary transfers, approvals, delegate/authority changes, account closures and unknown programs. Enforce low wallet balance, atomic spend caps, total exposure and daily loss limits, fresh quote/expiry, slippage and price-impact caps, idempotency, append-only audit logs, on-chain reconciliation and a global kill switch. The agent has no withdrawal/deposit or arbitrary-transfer capability.

Owner must be able to revoke Phantom app permissions and stop the agent. Treat all on-chain transactions as irreversible. See PHANTOM_SIGNING.md.
