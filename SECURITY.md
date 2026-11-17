# Security policy — MAYO MEME HUNTER

**Paper-only.** No wallet signing, transaction submission, private-key handling,
order-placement endpoints, or automated money transfers are implemented.

Never commit seed phrases, secret keys, RPC credentials, access tokens, or
transaction signing material. `.env` and likely key files are ignored.
Git history can retain secrets even after deletion; rotate a leaked key.

DEX Screener discovery is read-only and security data is incomplete.
Unknown on-chain authorities, ownership clustering, and sellability must
fail closed. A simulated paper sell is not a confirmed executable sale.

Before introducing any real trading adapter, require independent security
review, exact amount/fee caps, single-use order IDs, ledger reconciliation,
emergency pause controls, and **fresh explicit owner approval**. Never
unlock Mayo Kraken Trader as a side effect.
