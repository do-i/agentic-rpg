# tests/unit/world/test_world_map_overlays.py

from __future__ import annotations

from engine.world.world_map_overlays import WorldMapOverlays


class _StubOverlay:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"<Stub {self.name}>"


class TestActive:
    def test_none_when_empty(self):
        o = WorldMapOverlays()
        assert o.active is None
        assert o.any_active is False

    def test_dialogue_takes_priority_over_other_overlays(self):
        o = WorldMapOverlays()
        o.save_modal = _StubOverlay("save")
        o.inn = _StubOverlay("inn")
        o.dialogue = _StubOverlay("dialogue")
        assert o.active is o.dialogue

    def test_save_modal_picked_when_no_dialogue(self):
        o = WorldMapOverlays()
        o.save_modal = _StubOverlay("save")
        o.mc_shop = _StubOverlay("mc")
        assert o.active is o.save_modal

    def test_priority_chain_after_dialogue(self):
        order = ["save_modal", "mc_shop", "inn", "item_shop", "apothecary", "item_box_modal"]
        for keep in order:
            o = WorldMapOverlays()
            for name in order:
                setattr(o, name, _StubOverlay(name))
            # Clear everything above `keep` in the chain.
            i = order.index(keep)
            for name in order[:i]:
                setattr(o, name, None)
            assert o.active is getattr(o, keep), (
                f"with {keep} as highest, expected it to be active"
            )

    def test_any_active_true_with_one_set(self):
        o = WorldMapOverlays()
        o.item_box_modal = _StubOverlay("box")
        assert o.any_active is True


class TestRenderList:
    def test_empty_when_no_overlays(self):
        assert WorldMapOverlays().render_list() == []

    def test_only_non_none_overlays_returned(self):
        o = WorldMapOverlays()
        o.dialogue = _StubOverlay("dialogue")
        o.inn = _StubOverlay("inn")
        rendered = o.render_list()
        assert o.dialogue in rendered
        assert o.inn in rendered
        assert len(rendered) == 2

    def test_render_order_preserves_back_to_front(self):
        o = WorldMapOverlays()
        o.save_modal = _StubOverlay("save")
        o.dialogue = _StubOverlay("dialogue")
        o.mc_shop = _StubOverlay("mc")
        o.inn = _StubOverlay("inn")
        o.item_shop = _StubOverlay("item_shop")
        o.apothecary = _StubOverlay("apothecary")
        o.item_box_modal = _StubOverlay("box")
        rendered = o.render_list()
        assert rendered == [
            o.save_modal,
            o.dialogue,
            o.mc_shop,
            o.inn,
            o.item_shop,
            o.apothecary,
            o.item_box_modal,
        ]


class TestReset:
    def test_clears_every_slot(self):
        o = WorldMapOverlays()
        o.save_modal = _StubOverlay("save")
        o.dialogue = _StubOverlay("dialogue")
        o.mc_shop = _StubOverlay("mc")
        o.inn = _StubOverlay("inn")
        o.item_shop = _StubOverlay("item_shop")
        o.apothecary = _StubOverlay("apothecary")
        o.item_box_modal = _StubOverlay("box")

        o.reset()

        assert o.active is None
        assert o.any_active is False
        assert o.render_list() == []
