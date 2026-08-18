# Testing and certification

## Deterministic suite

The default tests do not depend on internet availability. They exercise the actual parser/scoring/store/API/export code using controlled source responses and a temporary SQLite database.

```bash
pytest -q
```

This is not a claim about live upstream availability. It proves local behavior and contracts.

## Live-source checks

A production deployment should additionally run bounded live probes with real credentials/network, for example:

```bash
gitgoblin scan databases --seed carlsverre --expand 0 --no-research
```

The resulting run artifact is stored under `data/artifacts/runs/` with an evidence hash. Live probes should be scheduled separately because source API availability/rate limits are external variables.

## Certificate

```bash
python -m gitgoblin.certify --output build/CERTIFICATE.json
```

Certification:

1. executes `pytest -q` unless `--skip-pytest` is supplied;
2. writes full stdout/stderr to `build/test.log`;
3. records return code/pass/fail;
4. hashes all GitGoblin source/config/schema files;
5. records Python/platform/version information.

A certificate with `tests_passed=false` is a failure, regardless of documentation claims.
