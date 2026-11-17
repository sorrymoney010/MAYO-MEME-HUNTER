# MAYO MEME HUNTER — Snag & Go

Independent Solana meme-coin discovery, analysis and automated-trading agent.

**Target behavior:** discover tokens, verify risk, buy qualified candidates, monitor positions, sell, and reconcile on-chain results. Live trading remains OFF until an isolated signer and all safety controls are complete.

## Current modules
- PumpPortal launch/migration collector (read-only).
- Solana RPC mint inspection (partial; Token-2022 extensions not decoded).
- DEX Screener discovery.
- Fee-aware paper trading, risk controls, wallet-history research and offline dashboard.
- Jupiter Swap API V2 order/execute boundary with hard policy caps and stale-signal/security gates. It accepts externally signed transactions but contains no signer or private-key handling.
- Offline tests and CI.

## Install and test
\`\`\`bash
git clone https://github.com/sorrymoney010/MAYO-MEME-HUNTER.git
cd MAYO-MEME-HUNTER
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
\`\`\`

## V2 commands
\`\`\`bash
mayo-meme stream --out data/solana_events.jsonl
mayo-meme inspect-mint --mint YOUR_TOKEN_MINT
mayo-meme scan --limit 10
mayo-meme replay --file examples/sample_snapshots.jsonl
\`\`\`

## Autonomous trading architecture
The intended pipeline is discovery -> security screening -> strategy signal -> fresh Jupiter quote -> isolated signer -> swap execution -> position monitoring -> automatic sell -> on-chain reconciliation.

The scaffold's hard ceilings are 0.05 SOL per buy, 0.20 SOL total daily buys, 5% price impact, 10-second signal freshness and two open positions. These are code ceilings, not an instruction to fund or activate the bot. The live switch is OFF by default.

Jupiter Swap API V2 uses \`GET /swap/v2/order\` for a quote and assembled unsigned transaction and \`POST /swap/v2/execute\` to land a signed transaction. See [Jupiter Swap API](https://developers.jup.ag/docs/swap) and [Order & Execute](https://developers.jup.ag/docs/swap/order-and-execute).

## Not live-ready yet
The signer is not implemented. We still need full Token-2022 and holder/creator analysis, real-time price/liquidity snapshots, durable event/position storage, automatic exit execution, restart-safe loss limits, transaction decoding/allowlisting, simulation, reconciliation, devnet testing and independent security review. Never paste a seed phrase/private key into source, chat, or configuration files.
