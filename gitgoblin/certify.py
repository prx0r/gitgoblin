from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .hashing import sha256_json


def source_manifest(root: Path) -> dict[str, str]:
    included_roots = [root / "gitgoblin", root / "configs", root / "schemas", root / "tests", root / "docs", root / "scripts"]
    root_files = [root / "pyproject.toml", root / "README.md", root / "AGENTS.md", root / "Dockerfile", root / "docker-compose.yml", root / "Makefile", root / "LICENSE-POLICY.md", root / ".env.example"]
    manifest: dict[str, str] = {}
    import hashlib
    for base in included_roots:
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            if path.suffix in {".py", ".yaml", ".yml", ".json", ".html", ".md", ".sh", ".toml"} or path.name in {"Dockerfile", "Makefile"}:
                manifest[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in root_files:
        if path.exists():
            manifest[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(sorted(manifest.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real GitGoblin certification")
    parser.add_argument("--output", default="build/CERTIFICATE.json")
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    build = root / "build"
    build.mkdir(parents=True, exist_ok=True)
    test_log = build / "test.log"

    if args.skip_pytest:
        test_returncode = None
        test_output = "pytest skipped by explicit --skip-pytest\n"
    else:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        test_returncode = proc.returncode
        test_output = proc.stdout
    test_log.write_text(test_output, encoding="utf-8")

    manifest = source_manifest(root)
    certificate = {
        "certificate_version": 1,
        "gitgoblin_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "pytest_invoked": not args.skip_pytest,
        "pytest_returncode": test_returncode,
        "tests_passed": None if args.skip_pytest else test_returncode == 0,
        "test_log": str(test_log.relative_to(root)),
        "test_log_sha256": __import__("hashlib").sha256(test_log.read_bytes()).hexdigest(),
        "source_manifest": manifest,
        "source_manifest_sha256": sha256_json(manifest),
    }
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(certificate, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(certificate, indent=2, sort_keys=True))
    if test_returncode not in (None, 0):
        raise SystemExit(test_returncode)


if __name__ == "__main__":
    main()
