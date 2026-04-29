# tests/unit/core/state/test_weighted_pick.py

from engine.util.weighted_pick import weighted_pick
from engine.util.pseudo_random import PseudoRandom


def make_rng(seed: int = 0) -> PseudoRandom:
    return PseudoRandom(seed=seed)


def test_empty_sequence_returns_none():
    assert weighted_pick(make_rng(), [], lambda e: 1) is None


def test_all_zero_weights_returns_none():
    rng = make_rng()
    pool = [{"id": "a"}, {"id": "b"}]
    assert weighted_pick(rng, pool, lambda e: 0) is None


def test_single_entry_always_picked():
    rng = make_rng()
    pool = [{"id": "only", "weight": 50}]
    picked = weighted_pick(rng, pool, lambda e: e["weight"])
    assert picked["id"] == "only"


def test_returns_one_of_the_input_entries():
    rng = make_rng()
    pool = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    picked = weighted_pick(rng, pool, lambda e: 1)
    assert picked in pool


def test_respects_weights_distribution():
    rng = make_rng(seed=42)
    pool = [{"id": "common", "w": 90}, {"id": "rare", "w": 10}]
    results = [weighted_pick(rng, pool, lambda e: e["w"]) for _ in range(400)]
    ids = [r["id"] for r in results]
    common_count = ids.count("common")
    rare_count = ids.count("rare")
    # common should heavily dominate; rare should still appear at least once.
    assert common_count > rare_count
    assert rare_count >= 1


def test_zero_weight_entries_skipped_when_others_have_weight():
    rng = make_rng(seed=1)
    pool = [{"id": "skip", "w": 0}, {"id": "always", "w": 100}]
    for _ in range(50):
        picked = weighted_pick(rng, pool, lambda e: e["w"])
        assert picked["id"] == "always"


def test_works_with_dataclass_like_objects():
    class E:
        def __init__(self, name, weight):
            self.name = name
            self.weight = weight

    rng = make_rng()
    pool = [E("a", 5), E("b", 5)]
    picked = weighted_pick(rng, pool, lambda e: e.weight)
    assert picked in pool
