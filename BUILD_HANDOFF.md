# MAYO MEME HUNTER — V2 engineering handoff

Official repo: https://github.com/sorrymoney010/MAYO-MEME-HUNTER
Separate from https://github.com/sorrymoney010/mayo-bot. Never modify or unlock the Kraken trader as part of this project.

## V2 implemented in this commit

- `stream.py`: one PumpPortal WebSocket connection; subscribes only to free `subscribeNewToken` and `subscribeMigration`; reconnects with exponential backoff; appends normalized JSONL events; stores provider raw payload and observed time. No trade/account stream, no transaction actions.
- `rpc.py`: read-only Solana JSON-RPC inspection for parsed mint authority/freeze authority, supply, largest token accounts and top-account concentration. Token-2022 remains unknown because extension parsing is not implemented.
- CLI: `mayo-meme stream`, `mayo-meme inspect-mint`.
- CI updated to install websocket dependency and run tests.

## V2 data source cost policy

PumpPortal docs list new-token and migration streams as free. Token/account trade streams are metered at 0.01 SOL per 10,000 messages and require an API key with a linked wallet funded to minimum balance. They are deliberately not subscribed by this code. One WebSocket connection must be reused. Verify current terms before future use.

References:
- https://pumpportal.fun/data-api/real-time/
- https://pumpportal.fun/fees/
- https://solana.com/docs/rpc/http
- https://solana.com/docs/tokens/basics/set-authority

## Known gaps (must not overstate security)

1. Launch/migration events only; not a complete market feed and no live price/volume/buyer aggregation yet.
2. Token-2022 extension parser missing: token_program_safe is UNKNOWN for Token-2022.
3. Largest accounts are not owner-deduplicated, so top-account concentration is only a rough upper bound.
4. Creator holdings, funding clusters, honeypot behavior, and executable sell route remain UNKNOWN.
5. PumpPortal payload schema can evolve; raw payload is retained for audit/reprocessing.
6. Public Solana RPC may rate limit; use a user-approved RPC endpoint for sustained collection.

## V2.1 next tasks

- SQLite append-only event store with signature/slot deduplication and gap tracking.
- Pair discovery after creation/migration; capture price, liquidity, volume, buys/sells with timestamps.
- Parse SPL Token-2022 extensions and resolve token account owners before concentration calculations.
- Check creator/deployer token holdings and wallet funding clusters.
- Obtain fresh size-specific sell quotes; quote availability is not guaranteed execution.
- Generate read-only candidate board and PAPER alerts only.
- Replay actual recorded data with latency, fees, priority fees, spreads, failed fills and delisted/rugged tokens.

No live executor is in scope. Any future real-money executor requires a separate architecture, audit, and explicit approval.
