# engine/util/weighted_pick.py
#
# Single shared weighted-choice helper.
#
# Both encounter_resolver (pick a Formation by weight) and battle_rewards
# (pick a loot pool entry by weight) used to carry their own _weighted_pick
# helper with a slightly different signature; this module unifies them.
#
# weight_fn returns the relative weight for an entry. If the total weight
# is zero (or the input is empty), returns None — callers treat that as
# "nothing to pick" rather than raising.

from __future__ import annotations

from typing import Callable, Sequence, TypeVar

from engine.util.pseudo_random import PseudoRandom


T = TypeVar("T")


def weighted_pick(
    rng: PseudoRandom,
    entries: Sequence[T],
    weight_fn: Callable[[T], int | float],
) -> T | None:
    """Pick one entry from `entries` weighted by weight_fn.

    Returns None if the sequence is empty or every weight is zero. Uses
    `rng.choices(...)` so the same RNG seed produces deterministic picks
    across both call sites.
    """
    if not entries:
        return None
    weights = [weight_fn(e) for e in entries]
    if sum(weights) == 0:
        return None
    return rng.choices(list(entries), weights=weights, k=1)[0]
