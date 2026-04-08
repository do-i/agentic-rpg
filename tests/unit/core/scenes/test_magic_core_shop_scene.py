# tests/unit/core/scenes/test_magic_core_shop_scene.py

from unittest.mock import MagicMock

from engine.service.repository_state import RepositoryState
from engine.dto.game_state_holder import GameStateHolder
from engine.scenes.magic_core_shop_scene import (
    MagicCoreShopScene, LARGE_RATE_THRESHOLD,
)


MC_SIZES = [
    ("mc_xl", "Magic Core (XL)", 10_000),
    ("mc_l",  "Magic Core (L)",   1_000),
    ("mc_m",  "Magic Core (M)",     100),
    ("mc_s",  "Magic Core (S)",      10),
    ("mc_xs", "Magic Core (XS)",      1),
]


def make_scene(repo=None, confirm_large=True):
    """Create a MagicCoreShopScene with a mocked holder."""
    if repo is None:
        repo = RepositoryState(gp=0)
    state = MagicMock()
    state.repository = repo
    holder = MagicMock(spec=GameStateHolder)
    holder.get.return_value = state

    on_close = MagicMock()
    scene = MagicCoreShopScene(
        holder=holder,
        scene_manager=MagicMock(),
        registry=MagicMock(),
        on_close=on_close,
        mc_sizes=MC_SIZES,
        confirm_large=confirm_large,
    )
    return scene, repo, on_close


class TestAvailable:
    def test_only_shows_owned(self):
        repo = RepositoryState(gp=0)
        repo.add_item("mc_m", 5)
        repo.get_item("mc_m").tags = {"magic_core"}
        repo.add_item("mc_xs", 10)
        repo.get_item("mc_xs").tags = {"magic_core"}

        scene, _, _ = make_scene(repo)
        avail = scene._available()
        assert [a[0] for a in avail] == ["mc_m", "mc_xs"]

    def test_empty_when_no_cores(self):
        scene, _, _ = make_scene()
        assert scene._available() == []


class TestExchange:
    def test_exchange_adds_gp_and_removes_items(self):
        repo = RepositoryState(gp=100)
        repo.add_item("mc_s", 5)
        repo.get_item("mc_s").tags = {"magic_core"}

        scene, _, _ = make_scene(repo)
        scene._list_sel = 0
        scene._state = "qty"
        scene._qty = 3

        scene._do_exchange()

        assert repo.gp == 130  # 100 + 3*10
        assert repo.get_item("mc_s").qty == 2

    def test_exchange_removes_entry_when_qty_zero(self):
        repo = RepositoryState(gp=0)
        repo.add_item("mc_xs", 2)
        repo.get_item("mc_xs").tags = {"magic_core"}

        scene, _, _ = make_scene(repo)
        scene._list_sel = 0
        scene._state = "qty"
        scene._qty = 2

        scene._do_exchange()

        assert repo.gp == 2
        assert repo.get_item("mc_xs") is None

    def test_exchange_clamps_qty_to_owned(self):
        repo = RepositoryState(gp=0)
        repo.add_item("mc_m", 3)
        repo.get_item("mc_m").tags = {"magic_core"}

        scene, _, _ = make_scene(repo)
        scene._list_sel = 0
        scene._state = "qty"
        scene._qty = 10  # more than owned

        scene._do_exchange()

        assert repo.gp == 300  # 3 * 100
        assert repo.get_item("mc_m") is None


class TestConfirmThreshold:
    def test_large_rate_triggers_confirm(self):
        assert 1_000 >= LARGE_RATE_THRESHOLD
        assert 10_000 >= LARGE_RATE_THRESHOLD

    def test_small_rate_below_threshold(self):
        assert 100 < LARGE_RATE_THRESHOLD
        assert 10 < LARGE_RATE_THRESHOLD
        assert 1 < LARGE_RATE_THRESHOLD
