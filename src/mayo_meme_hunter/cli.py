"""Command-line entry points. Deliberately no 'live' or 'trade' subcommand."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import PaperEngine, Snapshot
from .dashboard import render_dashboard
from .scanner import scan
from .wallets import analyze_wallet_events


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL line {line_no}: {exc}") from exc
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(prog="mayo-meme", description="MAYO MEME HUNTER: paper-only")
    sub = parser.add_subparsers(dest="cmd", required=True)
    scan_cmd = sub.add_parser("scan", help="Read-only DEX Screener discovery, UNVERIFIED watchlist")
    scan_cmd.add_argument("--limit", type=int, default=10)
    scan_cmd.add_argument("--out", type=Path)
    replay_cmd = sub.add_parser("replay", help="Replay JSONL observations with fee-aware paper fills")
    replay_cmd.add_argument("--file", type=Path, required=True)
    replay_cmd.add_argument("--out", type=Path)
    wallet_cmd = sub.add_parser("wallets", help="Analyze complete normalized wallet trade history")
    wallet_cmd.add_argument("--file", type=Path, required=True)
    wallet_cmd.add_argument("--out", type=Path)
    dash_cmd = sub.add_parser("dashboard", help="Generate static offline HTML from a replay JSON report")
    dash_cmd.add_argument("--file", type=Path, required=True)
    dash_cmd.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "dashboard":
        data = json.loads(args.file.read_text(encoding="utf-8"))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_dashboard(data), encoding="utf-8")
        print(f"Wrote paper-only dashboard to {args.out}")
        return
    if args.cmd == "scan":
        data = {"mode": "READ_ONLY", "results": scan(args.limit),
                "notice": "DEX Screener profiles are not a complete launch feed. Security is NOT verified."}
    elif args.cmd == "replay":
        engine = PaperEngine()
        for row in read_jsonl(args.file):
            engine.process(Snapshot.from_dict(row))
        data = engine.export()
    else:
        data = {"mode": "WALLET_RESEARCH_ONLY", "wallets": analyze_wallet_events(read_jsonl(args.file))}
    output = json.dumps(data, indent=2)
    print(output)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
