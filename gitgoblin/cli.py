from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from .api import create_app
from .db import Store
from .integrations.cuntgoblin import opportunity_to_cuntgoblin, signal_to_market_observations
from .pipeline.scout import Scout
from .settings import AppSettings, SectorProfile


def _profile(config_root: Path, sector: str) -> SectorProfile:
    path = config_root / "sectors" / f"{sector}.yaml"
    if not path.exists():
        raise SystemExit(f"Unknown sector profile: {path}")
    return SectorProfile.load(path)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gitgoblin", description="Frontier technical-attention intelligence")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--config-root", default="configs")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize the local store")

    p_seed = sub.add_parser("seed", help="Add a seed builder")
    p_seed.add_argument("sector")
    p_seed.add_argument("username")

    p_scan = sub.add_parser("scan", help="Run a live bounded scan")
    p_scan.add_argument("sector")
    p_scan.add_argument("--seed", action="append", default=[])
    p_scan.add_argument("--expand", type=int, default=2)
    p_scan.add_argument("--no-research", action="store_true")

    p_rank = sub.add_parser("rank", help="Show current signals")
    p_rank.add_argument("--sector")
    p_rank.add_argument("--limit", type=int, default=20)

    p_export = sub.add_parser("export", help="Export VentureLab-compatible JSON")
    p_export.add_argument("--sector")
    p_export.add_argument("--out", default="build/cuntgoblin-export.json")

    p_serve = sub.add_parser("serve", help="Serve API and dashboard")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8787)

    args = parser.parse_args()
    settings = AppSettings.load(args.config if Path(args.config).exists() else None)
    store = Store(settings.database_path)
    root = Path(args.config_root)

    if args.cmd == "init":
        print(json.dumps({"database": str(store.path), "status": "initialized"}, indent=2))
    elif args.cmd == "seed":
        _profile(root, args.sector)
        store.add_seed(args.sector, args.username.lower())
        print(json.dumps({"sector": args.sector, "seeds": store.seeds(args.sector)}, indent=2))
    elif args.cmd == "scan":
        profile = _profile(root, args.sector)
        run = Scout(store, settings, profile).run(
            args.seed or None, expand_per_seed=max(0, min(args.expand, 10)), research=not args.no_research
        )
        print(run.model_dump_json(indent=2))
    elif args.cmd == "rank":
        print(json.dumps([s.model_dump(mode="json") for s in store.signals(args.sector, args.limit)], indent=2))
    elif args.cmd == "export":
        payload = {
            "market_observations": [o for s in store.signals(args.sector, 1000) for o in signal_to_market_observations(s)],
            "opportunities": [opportunity_to_cuntgoblin(o) for o in store.opportunities(args.sector, 1000)],
        }
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(out)
    elif args.cmd == "serve":
        uvicorn.run(create_app(settings_path=args.config if Path(args.config).exists() else None, config_root=root), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
