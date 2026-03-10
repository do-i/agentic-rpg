
# 1. Party

## Composition
1 fixed protagonist (Hero class, scenario-defined) + 4 support members

## Formation

Front	Hero, Warrior
Back	SorCerer, Cleric, Rogue
Note: Rogue is flexible — can be front (melee) or back (ranged utility). You could encode this as an `attack_range: melee | ranged` flag per ability.

## Party-Wide Stats & Derived Values

Here's an elaborated Party system design, building on your existing notes:

## Formation

Since you have front/back row implicit in role design, consider formalizing it:

| Row | Members | Effect |
|---|---|---|
| Front | Hero, Warrior | Take full physical damage; deal full physical damage |
| Back | Sorcerer, Cleric, Rogue | Take reduced physical damage (×0.5); ranged/spell attacks unaffected |

Rogue is flexible — can be front (melee) or back (ranged utility). You could encode this as an `attack_range: melee | ranged` flag per ability.

## Party-Wide Stats & Derived Values

Stats that belong to the party (not a character):

| Stat | Source | Effect |
|---|---|---|
| `flee_rate` | Rogue's DEX (if in party) | Base flee 30%, +2% per Rogue DEX |
| `encounter_modifier` | Rogue passive | Reduces random encounter roll by ~20% |
| `trap_detect` | Rogue passive | Auto-reveal chest traps |
| `pt_balance` | Party Repository | Shared currency, always synced |

## Recruitment & Availability

Story-gated required joins (so party is always functionally complete)

## Status Effects on Party Members

Gaps to fill — status effect design:

| Effect | Cure | Who applies |
|---|---|---|
| `poison` | Cleric: Cure Status, item | Enemies |
| `sleep` | Taking damage, item | Enemies |
| `stun` | Wears off (1 turn) | Enemies |
| `silence` | Item | Enemies — blocks spell use |
| `taunt` | Wears off | Warrior ability — forces enemy targeting |
| `def_up` | Wears off | Hero: Rally |

Store active effects as a list on the member with a `duration` field.

## Death & Revival

- Member at `hp = 0` is **KO'd** — cannot act, cannot be targeted by enemies
- Cleric: **Revive** restores to `hp_max * 0.3`
- Item: `Phoenix Down` (or equivalent) — same effect
- If **all members KO'd** → Game Over

Party wipe handling: offer retry from last save. Possible to save the game at any place.

## Party UI Considerations

- **HUD during battle:** Row of member portraits with HP/MP bars — standard JRPG layout
- **Party screen (field):** List view, sortable; shows level, class, HP/MP, equipped weapon/armor
- **Active member highlight:** Whose turn it is gets a cursor/glow
- **KO state:** Portrait grayed out, HP shows 0
- Party order: player-arrangeable
- Last party memeber must join 10-15% of the story pass
- EXP is equal split. KO'ed member get 0
- Naming: player can name player-name. other members names are defined by scenario manifest
- Level cap 100
- EXP cap 1,000,000
- GP (Guild Point) cap 8,000,000
- STR, DEX, etc cap: 100
- each item type count cap: 100
