from gitgoblin.hashing import canonical_json, sha256_json, stable_id


def test_hash_is_order_independent_for_dicts():
    assert sha256_json({"a": 1, "b": 2}) == sha256_json({"b": 2, "a": 1})


def test_stable_id_is_stable():
    assert stable_id("x", {"k": [1, 2]}) == stable_id("x", {"k": [1, 2]})
    assert stable_id("x", {"k": [1, 2]}).startswith("x_")
