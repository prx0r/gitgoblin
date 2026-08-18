"""Mechanism extraction: identify valuable technical patterns in repositories."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Mechanism:
    mechanism_id: str
    name: str
    description: str
    category: str  # validation, state, routing, context, verification, compute, data, protocol
    evidence_files: tuple[str, ...] = ()
    evidence_snippets: tuple[str, ...] = ()
    confidence: float = 0.0
    targets: tuple[str, ...] = ()  # what QDW modules this applies to
    hypothesis: str = ""
    source_commit: str = ""
    source_repo: str = ""


# Pattern rules: keyword → mechanism mapping
MECHANISM_RULES: dict[str, list[dict[str, Any]]] = {
    "validation": [
        {"keywords": ["differential", "oracle", "reference impl", "cross-check"], "name": "Differential Testing", "description": "Validate against reference implementation"},
        {"keywords": ["fault injection", "chaos", "deliberately broken", "adversarial schedule"], "name": "Fault Injection", "description": "Deliberately break to test resilience"},
        {"keywords": ["mutation testing", "checker of checker", "seeded defective"], "name": "Mutation Testing", "description": "Test suite must catch seeded defects"},
        {"keywords": ["deterministic", "reproducible", "seed", "schedule"], "name": "Deterministic Testing", "description": "Reproducible test execution"},
        {"keywords": ["adversarial", "fuzz", "fuzzing", "property-based"], "name": "Adversarial Testing", "description": "Systematic adversarial input generation"},
    ],
    "state": [
        {"keywords": ["isolated", "per-object", "per-entity", "cell"], "name": "Isolated State", "description": "Per-entity isolated state management"},
        {"keywords": ["compare-and-swap", "cas", "optimistic concurrency"], "name": "CAS Coordination", "description": "Compare-and-swap coordination without consensus"},
        {"keywords": ["durable", "persistent", "crash-recoverable", "write-ahead"], "name": "Durable State", "description": "Crash-recoverable persistent state"},
        {"keywords": ["event sourced", "append-only", "event log", "immutable"], "name": "Event Sourcing", "description": "Append-only event log with projections"},
        {"keywords": ["replaceable", "ephemeral", "stateless node"], "name": "Replaceable Nodes", "description": "Nodes are stateless, state lives in storage"},
    ],
    "routing": [
        {"keywords": ["cost-aware", "cheapest", "budget", "spend limit"], "name": "Cost-Aware Routing", "description": "Route by cost constraints"},
        {"keywords": ["capability", "resolve", "match"], "name": "Capability Resolution", "description": "Match requests to capabilities"},
        {"keywords": ["fallback", "cascade", "retry"], "name": "Cascade Fallback", "description": "Ordered fallback routing"},
    ],
    "context": [
        {"keywords": ["context engineering", "curriculum", "playbook"], "name": "Context Engineering", "description": "Deliberately curated agent context"},
        {"keywords": ["agentic context", "evolving context", "self-improving"], "name": "Evolving Context", "description": "Context improves through use"},
        {"keywords": ["negative memory", "searched not found", "absence claim"], "name": "Negative Memory", "description": "Remember what was searched and not found"},
    ],
    "verification": [
        {"keywords": ["certificate", "receipt", "proof", "attestation"], "name": "Verifiable Receipt", "description": "Cryptographic proof of execution"},
        {"keywords": ["independent verifier", "separate verification", "authority"], "name": "Independent Verification", "description": "Verifier separate from executor"},
        {"keywords": ["pure decision", "deterministic core", "separated io"], "name": "Pure Decision Core", "description": "Deterministic logic separated from I/O"},
    ],
    "compute": [
        {"keywords": ["sandbox", "isolation", "container", "vm"], "name": "Execution Isolation", "description": "Isolated execution environment"},
        {"keywords": ["checkpoint", "resume", "snapshot"], "name": "Checkpoint/Resume", "description": "Save and restore execution state"},
    ],
    "data": [
        {"keywords": ["content-addressed", "hash store", "cas"], "name": "Content-Addressed Storage", "description": "Store by content hash"},
        {"keywords": ["merkle", "tree hash", "inclusion proof"], "name": "Merkle Tree", "description": "Merkle tree for integrity proofs"},
    ],
}


def extract_mechanisms(
    files: dict[str, str],
    *,
    repo: str = "",
    commit: str = "",
    max_mechanisms: int = 10,
) -> list[Mechanism]:
    """Extract mechanisms from repository files."""
    mechanisms: list[Mechanism] = []

    for filename, content in files.items():
        if not content:
            continue
        content_lower = content.lower()

        for category, rules in MECHANISM_RULES.items():
            for rule in rules:
                matches = [kw for kw in rule["keywords"] if kw in content_lower]
                if len(matches) >= 2:  # require at least 2 keyword matches
                    confidence = min(1.0, len(matches) * 0.25)
                    evidence_lines = []
                    for kw in matches[:3]:
                        for i, line in enumerate(content.split("\n")):
                            if kw in line.lower():
                                evidence_lines.append(f"{filename}:{i+1}: {line.strip()[:120]}")
                                break

                    name_key = rule["name"]
                    mech_id = f"mech_{hashlib.sha256(f'{name_key}:{filename}'.encode()).hexdigest()[:12]}"
                    mechanisms.append(Mechanism(
                        mechanism_id=mech_id,
                        name=rule["name"],
                        description=rule["description"],
                        category=category,
                        evidence_files=(filename,),
                        evidence_snippets=tuple(evidence_lines[:3]),
                        confidence=confidence,
                        source_repo=repo,
                        source_commit=commit,
                    ))

    # Deduplicate by name, keeping highest confidence
    seen: dict[str, Mechanism] = {}
    for m in mechanisms:
        key = m.name
        if key not in seen or m.confidence > seen[key].confidence:
            seen[key] = m

    return sorted(seen.values(), key=lambda m: m.confidence, reverse=True)[:max_mechanisms]


import hashlib
