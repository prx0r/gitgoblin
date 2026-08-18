from __future__ import annotations

import argparse
import time
from pathlib import Path

from .db import Store
from .pipeline.scout import Scout
from .settings import AppSettings, SectorProfile


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GitGoblin scans on a fixed interval")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--config-root", default="configs")
    parser.add_argument("--sector", action="append", required=True)
    parser.add_argument("--interval", type=int, default=21600, help="Seconds between cycles; default 6h")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = AppSettings.load(args.config if Path(args.config).exists() else None)
    store = Store(settings.database_path)
    root = Path(args.config_root)
    while True:
        for sector in args.sector:
            profile = SectorProfile.load(root / "sectors" / f"{sector}.yaml")
            Scout(store, settings, profile).run()
        if args.once:
            break
        time.sleep(max(300, args.interval))


if __name__ == "__main__":
    main()
