# GitGoblin Trust Model

## What GitGoblin IS

A **technical frontier intelligence** system that:
- Watches repositories, papers, releases, and developer activity
- Detects convergence signals when multiple experts关注 the same target
- Extracts technical mechanisms from code and documentation
- Mines agent context files (AGENTS.md, CLAUDE.md, etc.)
- Derives BUILD/RESEARCH/WATCH/REJECT opportunities

## What GitGoblin is NOT

- **Not a prediction engine.** It detects patterns, not futures.
- **Not a recommendation system.** It surfaces evidence, not advice.
- **Not a source of truth.** It's a sensor — observations may be stale, incomplete, or misleading.
- **Not a replacement for human judgment.** Opportunities are hypotheses, not conclusions.

## What GitGoblin DOES NOT prove

1. **That a repository is "good" or "important."** It measures attention convergence, not quality.
2. **That a mechanism will work in your context.** It extracts patterns, not guarantees.
3. **That a signal will persist.** Markets change, projects die, experts shift focus.
4. **That the data is complete.** It only sees what its sources see.
5. **That the scoring is objective.** Scoring involves priors and assumptions.

## What GitGoblin DOES prove

1. **Observations are immutable.** Once stored, raw observations cannot be modified.
2. **Evidence chains are traceable.** Every signal traces back to raw observations with hashes.
3. **Source health is monitored.** Failed sources are tracked and flagged.
4. **Freshness is enforced.** Data expires according to configurable TTLs.
5. **Derivation is recorded.** Every inference is logged with inputs, outputs, and software version.

## Confidence Levels

| Level | Meaning | Use |
|-------|---------|-----|
| 0.9-1.0 | High confidence, strong evidence | Direct use |
| 0.7-0.9 | Moderate confidence, some evidence | Review recommended |
| 0.5-0.7 | Low confidence, weak evidence | Research before acting |
| <0.5 | Speculative, minimal evidence | Informational only |

## Rate Limits

| Source | Limit | Policy |
|--------|-------|--------|
| GitHub | 1 req/3s | Token bucket with Retry-After |
| OpenAlex | 1 req/0.5s | Polite pool, $1/day cap |
| arXiv | 1 req/3.5s | Required 3s+ delay |
| HackerNews | 1 req/1s | Be-nice policy |
| RSS | 1 req/30s per feed | Publisher tolerance |
| ecosyste.ms | 1 req/5s | Conservative |
