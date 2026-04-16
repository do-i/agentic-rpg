import random as _random


class PseudoRandom:
    """
    Seeded wrapper around random.Random.
    Inject this singleton instead of using the module-level random functions
    so that record/playback sessions are fully reproducible.
    """

    def __init__(self, seed: int) -> None:
        self._rng = _random.Random(seed)

    def random(self) -> float:
        return self._rng.random()

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def choice(self, seq):
        return self._rng.choice(seq)

    def choices(self, population, weights=None, k: int = 1):
        return self._rng.choices(population, weights=weights, k=k)
