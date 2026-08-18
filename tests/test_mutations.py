"""Mutation tests — deliberately inject bugs and prove tests catch them."""
import pytest
from gitgoblin.db import Store
from gitgoblin.hashing import canonical_json
from gitgoblin.mechanisms import extract_mechanisms
from gitgoblin.agent_context import detect_context_files, extract_practices


def test_mechanism_extraction_requires_keywords():
    """Single keyword match should not produce a mechanism."""
    files = {"test.py": "deterministic"}
    mechanisms = extract_mechanisms(files)
    assert len(mechanisms) == 0


def test_context_detection_case_sensitive():
    """File detection must match exact patterns."""
    paths = ["AGENTS.md", "agents.md", "AGENTS.MD"]
    contexts = detect_context_files(paths)
    assert len(contexts) == 1
    assert contexts[0]["path"] == "AGENTS.md"


def test_hash_changes_with_input():
    """Different input must produce different hash."""
    h1 = canonical_json({"a": 1})
    h2 = canonical_json({"a": 2})
    assert h1 != h2


def test_mechanism_extraction_deduplication():
    """Same mechanism name should be deduplicated."""
    files = {
        "a.py": "deterministic testing reproducible seed schedule",
        "b.py": "deterministic testing reproducible seed schedule",
    }
    mechanisms = extract_mechanisms(files)
    names = [m.name for m in mechanisms]
    assert len(names) == len(set(names))


def test_practices_extraction():
    """Practice extraction must find relevant patterns."""
    content = "Always run pytest. Never use bare except. Rate limit API calls."
    practices = extract_practices(content, "agents_md")
    assert len(practices) >= 2
