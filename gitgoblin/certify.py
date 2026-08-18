"""Final certificate — automated PASS/FAIL with git SHA + schema version.

Modeled after Dell's certify_final.py.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TestSuiteResult:
    name: str
    passed: int
    failed: int
    skipped: int
    duration_seconds: float

    @property
    def status(self) -> str:
        return "PASS" if self.failed == 0 else "FAIL"

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped


@dataclass(frozen=True)
class BuildCertificate:
    git_sha: str
    schema_version: str
    scoring_version: str
    test_suites: tuple[TestSuiteResult, ...]
    structural_gates: dict[str, bool]
    source_tree_hash: str
    issued_at: str

    @property
    def status(self) -> str:
        return "PASS" if all(s.failed == 0 for s in self.test_suites) and all(self.structural_gates.values()) else "FAIL"

    @property
    def total_tests(self) -> int:
        return sum(s.total for s in self.test_suites)

    @property
    def total_passed(self) -> int:
        return sum(s.passed for s in self.test_suites)

    @property
    def total_failed(self) -> int:
        return sum(s.failed for s in self.test_suites)

    @property
    def certificate_hash(self) -> str:
        return "sha256:" + hashlib.sha256(json.dumps(asdict(self), sort_keys=True, default=str).encode()).hexdigest()


def get_git_sha(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_path),
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def compute_source_tree_hash(repo_path: Path) -> str:
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
    return "sha256:" + hashlib.sha256("\n".join(hashes).encode()).hexdigest()


def run_test_suite(name: str, command: str, cwd: Path) -> TestSuiteResult:
    """Run a test suite and parse results."""
    import time
    start = time.time()
    try:
        result = subprocess.run(
            command, shell=True, cwd=str(cwd),
            capture_output=True, text=True, timeout=300
        )
        duration = time.time() - start
        output = result.stdout + result.stderr

        # Parse pytest output
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        skipped = output.count(" SKIPPED")
        errors = output.count(" ERROR")

        return TestSuiteResult(
            name=name,
            passed=passed,
            failed=failed + errors,
            skipped=skipped,
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired:
        return TestSuiteResult(name=name, passed=0, failed=1, skipped=0, duration_seconds=300)
    except Exception as e:
        return TestSuiteResult(name=name, passed=0, failed=1, skipped=0, duration_seconds=0)


def certify(
    repo_path: Path,
    *,
    schema_version: str = "v0.2",
    scoring_version: str = "v1.0",
) -> BuildCertificate:
    """Run all test suites and produce a BuildCertificate."""
    suites = [
        run_test_suite("invariants", "python3 -m pytest tests/test_invariants.py -v", repo_path),
        run_test_suite("mutations", "python3 -m pytest tests/test_mutations.py -v", repo_path),
        run_test_suite("core", "python3 -m pytest tests/ -v --ignore=tests/test_invariants.py --ignore=tests/test_mutations.py --ignore=tests/test_mcp.py", repo_path),
    ]

    structural_gates = {
        "all_suites_pass": all(s.failed == 0 for s in suites),
        "tests_executed": all(s.total > 0 for s in suites),
        "no_skipped_critical": all(s.skipped < s.total for s in suites),
    }

    cert = BuildCertificate(
        git_sha=get_git_sha(repo_path),
        schema_version=schema_version,
        scoring_version=scoring_version,
        test_suites=tuple(suites),
        structural_gates=structural_gates,
        source_tree_hash=compute_source_tree_hash(repo_path),
        issued_at=datetime.now(UTC).isoformat(),
    )

    return cert


def save_certificate(cert: BuildCertificate, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "BUILD_CERTIFICATE.json"
    cert_path.write_text(json.dumps(asdict(cert), indent=2, sort_keys=True, default=str), encoding="utf-8")
    return cert_path
