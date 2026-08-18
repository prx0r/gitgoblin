"""Agent context mining: detect and version AGENTS.md, CLAUDE.md, repo rules, etc."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentContext:
    context_id: str
    file_path: str
    context_type: str  # agents_md, claude_md, repo_rules, review_guidelines, testing_doctrine, architecture
    content_hash: str
    size_bytes: int
    title: str
    summary: str
    practices: tuple[str, ...] = ()
    version: str = ""


# Known agent context file patterns
CONTEXT_PATTERNS: list[dict[str, Any]] = [
    {"pattern": r"AGENTS\.md$", "type": "agents_md", "label": "Agent Instructions"},
    {"pattern": r"CLAUDE\.md$", "type": "claude_md", "label": "Claude Instructions"},
    {"pattern": r"\.github/copilot-instructions\.md$", "type": "copilot", "label": "Copilot Instructions"},
    {"pattern": r"CONTRIBUTING\.md$", "type": "contributing", "label": "Contributing Guide"},
    {"pattern": r"TESTING\.md$", "type": "testing_doctrine", "label": "Testing Doctrine"},
    {"pattern": r"ARCHITECTURE\.md$", "type": "architecture", "label": "Architecture Docs"},
    {"pattern": r"docs/.*(?:architecture|design|testing|contributing).*\.md$", "type": "architecture", "label": "Design Docs"},
    {"pattern": r"\.cursorrules$", "type": "cursor_rules", "label": "Cursor Rules"},
    {"pattern": r"\.github/CODEOWNERS$", "type": "codeowners", "label": "Code Owners"},
    {"pattern": r"docs/SECURITY\.md$", "type": "security", "label": "Security Policy"},
]


def detect_context_files(file_paths: list[str]) -> list[dict[str, str]]:
    """Detect agent context files from a list of file paths."""
    results = []
    for path in file_paths:
        for pattern_def in CONTEXT_PATTERNS:
            if re.search(pattern_def["pattern"], path):
                results.append({"path": path, "type": pattern_def["type"], "label": pattern_def["label"]})
                break
    return results


def extract_practices(content: str, context_type: str) -> tuple[str, ...]:
    """Extract key practices from agent context content."""
    practices = []
    content_lower = content.lower()

    # Common practice patterns
    practice_patterns = [
        (r"(?:must|shall|always|always use|never use|do not use)", "rule"),
        (r"(?:test|testing|pytest|unittest)", "testing"),
        (r"(?:lint|format|black|ruff|mypy)", "code_quality"),
        (r"(?:commit|conventional|squash|rebase)", "git_workflow"),
        (r"(?:review|pr|pull request)", "review_process"),
        (r"(?:security|vulnerability|secret)", "security"),
        (r"(?:benchmark|performance|latency)", "performance"),
        (r"(?:error|exception|fallback)", "error_handling"),
        (r"(?:cache|memoize|invalidate)", "caching"),
        (r"(?:rate.?limit|throttle|backoff)", "rate_limiting"),
    ]

    for pattern, practice_type in practice_patterns:
        matches = re.findall(pattern, content_lower)
        if matches:
            practices.append(f"{practice_type}({len(matches)})")

    return tuple(practices)


def build_agent_context(file_path: str, content: str, content_hash: str) -> AgentContext:
    """Build AgentContext from a file."""
    for pattern_def in CONTEXT_PATTERNS:
        if re.search(pattern_def["pattern"], file_path):
            practices = extract_practices(content, pattern_def["type"])
            # Extract first meaningful line as title
            lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
            title = lines[0][:100] if lines else file_path

            return AgentContext(
                context_id=f"ctx_{content_hash[:16]}",
                file_path=file_path,
                context_type=pattern_def["type"],
                content_hash=content_hash,
                size_bytes=len(content.encode()),
                title=title,
                summary=f"{pattern_def['label']}: {len(practices)} practices detected",
                practices=practices,
            )

    return AgentContext(
        context_id=f"ctx_{content_hash[:16]}",
        file_path=file_path,
        context_type="unknown",
        content_hash=content_hash,
        size_bytes=len(content.encode()),
        title=file_path,
        summary="Unknown context type",
    )
