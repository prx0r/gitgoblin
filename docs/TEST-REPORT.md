# GitGoblin v0.1.0 — Test report

Generated: 2026-08-18 UTC

## Executed gates

1. `python -m pytest -q`
   - Result: **22 passed**
   - Covers deterministic hashing/idempotency, SQLite append semantics, licensing classification, builder/signal scoring, primitive/opportunity generation, API endpoints, GitHub normalization, OpenAlex, arXiv, ecosyste.ms, RSS, Hacker News, HTTP cache/retry behavior, and full Scout → signal → opportunity → cuntgoblin export.
2. `python -m pytest --cov=gitgoblin --cov-report=term -q`
   - Result: **22 passed**
   - Overall statement coverage: **77%**.
   - High-value deterministic paths: DB 92%, GitHub collector 94%, Hacker News 96%, OpenAlex 92%, arXiv 97%, expertise 94%, signals 93%, primitives 97%, opportunity engine 87%, cuntgoblin adapter 100%.
3. `python -m compileall -q gitgoblin`
   - Result: pass.
4. Editable packaging smoke: `python -m pip install -e . --no-deps --no-build-isolation`
   - Result: pass after switching the build backend to locally available setuptools.
5. Wheel packaging: `python -m pip wheel . --no-deps --no-build-isolation -w build/dist`
   - Result: pass; produced `gitgoblin-0.1.0-py3-none-any.whl`.
6. Wheel CLI smoke
   - First nested-venv attempt: failed because the temporary venv did not inherit the managed environment's installed `uvicorn`; this was an environment/dependency-isolation failure, not suppressed.
   - Dependency-complete environment: force-installed the built wheel, ran `gitgoblin --help` from `/tmp` outside the source tree, imported `gitgoblin`, and verified version `0.1.0`: **pass**.
   - CLI exposes `init`, `seed`, `scan`, `rank`, `export`, `serve`.
7. `python -m gitgoblin.certify --output build/CERTIFICATE.json`
   - Runs pytest itself, hashes the test log and every source/config/schema/test file, and emits a reproducible machine-readable certificate.

## What was deliberately not claimed

The build environment has no unrestricted outbound Internet from normal Python/container execution, so the test suite does **not** claim a live GitHub/OpenAlex/arXiv/HN request was executed from this container. Network adapters are tested against deterministic HTTP response shapes and failure behavior; current endpoint/terms constraints were separately verified during web research and are documented in `docs/RESEARCH.md`.

A Docker image build was not executed because Docker availability is not assumed in the artifact environment. The Dockerfile and Compose file are included, but this is not recorded as a passed gate.

The optional LLM architecture-enrichment adapter is excluded from core correctness. GitGoblin's scoring, evidence, convergence and opportunity decisions remain deterministic without it.

## Anti-fake-test policy

- Test fixtures are explicitly marked `is_test_fixture=true` where they enter the observation store.
- Normal production reads exclude test fixtures by default.
- The end-to-end test uses deterministic synthetic source responses solely to exercise orchestration; it cannot contaminate production scoring state.
- Certification stores a SHA-256 manifest and test-log hash rather than a prose-only claim.
