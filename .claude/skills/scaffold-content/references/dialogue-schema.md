# Dialogue Schema — Full Reference

Dialogue files live at `rusted_kingdoms/data/dialogue/<id>.yaml`.
The `id` in the filename must match the `id` field inside.

## Types

- `npc` — conditional dialogue for NPCs (different lines based on flags)
- `cutscene` — linear cutscene, no conditions

---

## NPC Dialogue — Full Schema

```yaml
id: guard_east_gate
type: npc
entries:
  - condition:
      requires: []       # flags that must be SET
      excludes: []       # flags that must NOT be set
    lines:
      - "Halt! The east road is closed."
      - "Turn back, traveler."
    on_complete:
      set_flag: talked_to_guard_east
      # set_flag can also be a list: [flag_a, flag_b]

  - condition:
      requires: [talked_to_guard_east]
      excludes: [gate_opened]
    lines:
      - "I told you, the road is closed."

  - condition:
      requires: [gate_opened]
    lines:
      - "The road is open. Travel safely."
```

Entries are evaluated top-to-bottom; the first matching condition is used.
An entry with no `condition` block always matches (useful as a fallback last entry).

---

## Cutscene — Full Schema

```yaml
id: intro_throne_room
type: cutscene
lines:
  - "The king surveys the ruined kingdom."
  - "\"There is little time,\" he says."
on_complete:
  set_flag: intro_complete
  transition:
    map: overworld
    position: [10, 15]
    fade: in
```

---

## on_complete Actions (all optional, mix as needed)

```yaml
on_complete:
  set_flag: <flag_id>          # string or list of strings
  give_items:
    - id: <item_id>
      qty: 1
  join_party: <character_id>
  transition:
    map: <map_id>
    position: [x, y]
    fade: in                   # in | out
  start_battle: <enemy_id>
  open_shop: true
  open_inn: true
  open_apothecary: true
```

---

## Wiring Dialogue to an NPC

After creating the dialogue file, add the NPC entry to the appropriate map YAML at `rusted_kingdoms/data/maps/<map_id>.yaml`:

```yaml
npcs:
  - id: guard_east
    name: Guard
    position: [12, 8]
    dialogue: guard_east_gate    # matches the dialogue file id
    sprite: assets/sprites/npcs/guard.tsx
    default_facing: down
    animation:
      mode: still
    present:
      requires: []
      excludes: []
    availability: 1.0
```

If the dialogue is for a shop, inn, or apothecary keeper, include the relevant `open_shop: true` etc. in the dialogue's `on_complete`.
