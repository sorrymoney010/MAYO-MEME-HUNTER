# MAYO MEME HUNTER — Snag & Go

Independent Solana meme-coin discovery and autonomous-trading project. **Proposed owner wallet: a dedicated Phantom account.**

**Live trading is hard-disabled.** This build can collect and analyze data, paper trade, and prepare Jupiter quotes. It cannot sign or submit a real transaction.

## Capabilities
- PumpPortal launch/migration collector (read-only).
- Solana RPC mint inspection (partial; Token-2022 extensions not decoded).
- DEX Screener discovery.
- Fee-aware paper trading, risk controls, wallet-history research and offline dashboard.
- Jupiter Swap API V2 quote preparation with candidate/security/sellability gates.
- Phantom isolated-signing design in [PHANTOM_SIGNING.md](PHANTOM_SIGNING.md).
- Offline tests and CI.

## Wallet model
Use a new, dedicated MAYO account in Phantom, separate from long-term holdings. Never share or export the recovery phrase/private key to the agent. Start with owner-reviewed Phantom signatures. Phantom documents Auto-Confirm for certain supported apps (including Jupiter), but MAYO must not assume it is supported; if Phantom does not show Auto-Confirm for MAYO, the integration remains manual. The documented Auto-Confirm session is limited to up to 10 transactions/minute for two hours and can be revoked.

If 24/7 autonomous signing is not supported through Phantom's official connection mechanism, the alternative is a separate KMS/HSM/MPC-managed low-balance trading wallet, with Phantom retained as the owner's oversight wallet. That is a separate approval decision.

## Install and test
```bash
git clone https://github.com/sorrymoney010/MAYO-MEME-HUNTER.git
cd MAYO-MEME-HUNTER
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Commands
```bash
mayo-meme stream --out data/solana_events.jsonl
mayo-meme inspect-mint --mint YOUR_TOKEN_MINT
mayo-meme scan --limit 10
mayo-meme replay --file examples/sample_snapshots.jsonl
```

## Not live-ready
The signer, transaction parser/allowlist, persistent atomic spend ledger, full token-security analysis, live market snapshots, position monitor, automatic sell execution, daily-loss stop, transaction reconciliation and independent security review are not complete. Do not add private keys to source or environment files. See the signing design before implementing any wallet integration.
