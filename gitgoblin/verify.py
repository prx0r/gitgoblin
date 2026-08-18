"""QDW-style verification: VerificationPlan → VerificationRun → CommandReceipt → Certificate.

Replaces the old certify.py with evidence-bound verification.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .hashing import sha256_json, canonical_json


@dataclass(frozen=True)
class CommandReceipt:
    command: str
    exit_code: int
    stdout_hash: str
    stderr_hash: str
    duration_ms: int
    executed_at: str

    @property
    def receipt_hash(self) -> str:
        return sha256_json(asdict(self))


@dataclass(frozen=True)
class VerificationRun:
    run_id: str
    plan_id: str
    command_receipts: list[CommandReceipt]
    source_manifest_hash: str
    started_at: str
    finished_at: str
    status: str  # PASS | FAIL

    @property
    def run_hash(self) -> str:
        return sha256_json(asdict(self))


@dataclass(frozen=True)
class BuildCertificate:
    certificate_id: str
    verification_run_id: str
    source_manifest_hash: str
    source_tree_hash: str
    run_hash: str
    command_receipt_hashes: list[str]
    schema_version: str
    scoring_version: str
    issued_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def certificate_hash(self) -> str:
        return sha256_json(asdict(self))


def compute_tree_hash(repo_path: Path) -> str:
    """Compute SHA-256 of all source files (excluding .git, __pycache__, .venv, data)."""
    hashes = []
    exclude = {".git", "__pycache__", ".venv", "data", ".pytest_cache", "node_modules", "build", "dist"}
    for path in sorted(repo_path.rglob("*")):
        if path.is_file() and not any(part in exclude for part in path.parts):
            try:
                h = hashlib.sha256(path.read_bytes()).hexdigest()
                rel = str(path.relative_to(repo_path))
                hashes.append(f"{rel}:{h}")
            except (PermissionError, OSError):
                continue
    combined = "\n".join(hashes)
    return "sha256:" + hashlib.sha256(combined.encode()).hexdigest()


def compute_source_manifest(repo_path: Path) -> dict[str, Any]:
    """Compute source manifest with file hashes and metadata."""
    files = {}
    exclude = {".git", "__pycache__", ".venv", "data", ".pytest_cache", "node_modules", "build", "dist"}
    for path in sorted(repo_path.rglob("*")):
        if path.is_file() and not any(part in exclude for part in path.parts):
            try:
                rel = str(path.relative_to(repo_path))
                h = hashlib.sha256(path.read_bytes()).hexdigest()
                files[rel] = {"sha256": h, "size": path.stat().st_size}
            except (PermissionError, OSError):
                continue
    return {
        "repo": str(repo_path),
        "file_count": len(files),
        "files": files,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def run_command(cmd: str, cwd: Path, timeout: int = 120) -> CommandReceipt:
    """Run a command and return a receipt."""
    import time
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandReceipt(
            command=cmd,
            exit_code=result.returncode,
            stdout_hash="sha256:" + hashlib.sha256(result.stdout.encode()).hexdigest(),
            stderr_hash="sha256:" + hashlib.sha256(result.stderr.encode()).hexdigest(),
            duration_ms=duration_ms,
            executed_at=datetime.now(timezone.utc).isoformat(),
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CommandReceipt(
            command=cmd,
            exit_code=-1,
            stdout_hash="sha256:" + hashlib.sha256(b"TIMEOUT").hexdigest(),
            stderr_hash="sha256:" + hashlib.sha256(b"Command timed out".encode()).hexdigest(),
            duration_ms=duration_ms,
            executed_at=datetime.now(timezone.utc).isoformat(),
        )


def verify(
    repo_path: Path,
    commands: list[str],
    *,
    schema_version: str = "v0.2",
    scoring_version: str = "v1.0",
    metadata: dict[str, Any] | None = None,
) -> BuildCertificate:
    """Run verification commands and produce a QDW-style BuildCertificate."""
    plan_id = "plan_" + sha256_json({"repo": str(repo_path), "commands": commands})[:16]
    run_id = "run_" + sha256_json({"plan": plan_id, "time": datetime.now(timezone.utc).isoformat()})[:16]

    source_manifest = compute_source_manifest(repo_path)
    source_manifest_hash = sha256_json(source_manifest)
    source_tree_hash = compute_tree_hash(repo_path)

    started_at = datetime.now(timezone.utc).isoformat()
    receipts = []
    all_passed = True
    for cmd in commands:
        receipt = run_command(cmd, repo_path)
        receipts.append(receipt)
        if receipt.exit_code != 0:
            all_passed = False

    finished_at = datetime.now(timezone.utc).isoformat()

    verification_run = VerificationRun(
        run_id=run_id,
        plan_id=plan_id,
        command_receipts=receipts,
        source_manifest_hash=source_manifest_hash,
        started_at=started_at,
        finished_at=finished_at,
        status="PASS" if all_passed else "FAIL",
    )

    cert_id = "cert_" + sha256_json({"run": verification_run.run_hash, "time": finished_at})[:16]
    certificate = BuildCertificate(
        certificate_id=cert_id,
        verification_run_id=run_id,
        source_manifest_hash=source_manifest_hash,
        source_tree_hash=source_tree_hash,
        run_hash=verification_run.run_hash,
        command_receipt_hashes=[r.receipt_hash for r in receipts],
        schema_version=schema_version,
        scoring_version=scoring_version,
        issued_at=finished_at,
        metadata=metadata or {},
    )

    return certificate


def save_certificate(cert: BuildCertificate, output_dir: Path) -> Path:
    """Save certificate and manifest to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "BUILD_CERTIFICATE.json"
    cert_path.write_text(json.dumps(asdict(cert), indent=2, sort_keys=True), encoding="utf-8")
    return cert_path
