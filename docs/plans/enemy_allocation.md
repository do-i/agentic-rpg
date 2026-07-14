# Enemy Allocation — Rusted Kingdoms

This document records the post-rebuild enemy roster and zone allocation. Every enemy id is also a sprite filename in `rusted_kingdoms/assets/sprites/enemies/{id}.png`. Stats follow the bands in `docs/design/enemy.md` (per-zone HP/ATK/DEF/MRES/DEX/EXP) with type modifiers (beast=base, undead +10%HP/+15%MRES/-10%DEX, construct +20%HP/+25%DEF/-20%MRES/-15%DEX, demon +15%ATK/+10%MRES/+10%DEX, humanoid=base).

## Zone allocation overview

| # | Zone | Tier | Theme | Mooks | Boss | Barrier |
|---|---|---|---|---|---|---|
| 1 | Starting Forest | F | Goblin scouts in light woods | 5 | grik_the_grin | — |
| 2 | Open Plains | E | Bandit critters, lone wolves | 7 | wolf_beast_black_fur | — |
| 3 | Marshland | D | Sewer ratfolk, bat fiends | 8 | ratkin_plague_doctor_black_mask_doctor | — |
| 4 | Ancient Ruins | C | Restless dead | 10 | skeleton_knight_base | bat_demon_red_wing_fiend (veil_breaker) |
| 5 | Mountain Foothills | B | Goblin engineering corps + frankenstein | 8 | titch_the_ticker_171 | pumpkin_jack_lantern_duelist (veil_breaker) |
| 6 | Mountain Pass | A | Orc warband | 8 | orc_shaman_red_hood_shaman | — |
| 7 | Sunken Cave | A→S | Lizardmen, drowned pirates, withered bones | 9 | pirate_captain_eyepatch_captain | — |
| 8 | Corrupted Forest | S | Dark fey, harvest cult, swamp trolls | 10 | troll_shaman_base | — |
| 9 | Volcanic Region | S | Beastmen brutes, dragon-blooded lizardguard | 12 | wartotaur_warlord_blackhorn_chief | — |
| 10 | Final Stronghold | SS | Vampire court, fallen heaven, alien crystal invasion | 16 | fallen_angel_red_judicator | — |

Total: 93 mook entries + 10 bosses = **103 sprites placed (100% coverage of `assets/sprites/enemies/`)**.

## Per-enemy stat snapshot

Format: `id` — name (type) — HP / ATK / DEF / MRES / DEX / EXP.

### Zone 1 — Starting Forest (Rank F)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| goblin | Goblin | humanoid | 25 | 9 | 3 | 2 | 12 | 24 |
| goblin_warrior | Goblin Warrior | humanoid | 35 | 11 | 5 | 3 | 10 | 34 |
| goblin_scout_base | Goblin Scout | humanoid | 22 | 10 | 3 | 2 | 12 | 26 |
| goblin_scout_sling_scout | Sling Scout | humanoid | 24 | 11 | 4 | 3 | 11 | 28 |
| goblin_scout_hooded_goblin | Hooded Goblin | humanoid | 28 | 11 | 4 | 3 | 12 | 30 |
| **grik_the_grin** ★ | Grik the Grin | beast | 33 | 11 | 4 | 3 | 14 | 36 |

### Zone 2 — Open Plains (Rank E)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| rabbit_bandit_base | Rabbit Bandit | beast | 38 | 12 | 5 | 3 | 13 | 40 |
| rabbit_bandit_brown_rabbit | Brown Rabbit | beast | 36 | 13 | 5 | 3 | 14 | 42 |
| rabbit_bandit_knife_bandit | Knife Bandit | humanoid | 40 | 14 | 6 | 4 | 14 | 48 |
| mouse_thief_base | Mouse Thief | beast | 35 | 13 | 5 | 4 | 14 | 44 |
| mouse_thief_white_mouse | White Mouse | beast | 36 | 13 | 5 | 5 | 14 | 46 |
| wolf_beast_base | Plains Wolf | beast | 50 | 14 | 6 | 4 | 13 | 52 |
| wolf_beast_spear_beast | Spear Beast | humanoid | 52 | 15 | 7 | 5 | 12 | 56 |
| **wolf_beast_black_fur** ★ | Black Fur Alpha | beast | 130 | 22 | 11 | 8 | 18 | 180 |

### Zone 3 — Marshland (Rank D)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| ratkin_cutpurse_base | Ratkin Cutpurse | humanoid | 58 | 15 | 8 | 6 | 15 | 65 |
| ratkin_cutpurse_sewer_archer | Sewer Archer | humanoid | 56 | 16 | 8 | 6 | 16 | 70 |
| ratkin_cutpurse_masked_scavenger | Masked Scavenger | humanoid | 62 | 16 | 9 | 7 | 14 | 72 |
| ratkin_plague_doctor_base | Plague Doctor | humanoid | 60 | 16 | 8 | 8 | 13 | 75 |
| ratkin_plague_doctor_sewer_physician | Sewer Physician | humanoid | 64 | 17 | 9 | 8 | 13 | 80 |
| bat_demon_base | Bat Demon | demon | 55 | 21 | 8 | 9 | 18 | 78 |
| bat_demon_night_fiend | Night Fiend | demon | 58 | 21 | 9 | 9 | 19 | 82 |
| mouse_thief_mouse_archer | Mouse Archer | beast | 52 | 17 | 7 | 6 | 16 | 70 |
| **ratkin_plague_doctor_black_mask_doctor** ★ | Black Mask Doctor | humanoid | 135 | 24 | 14 | 14 | 16 | 235 |

### Zone 4 — Ancient Ruins (Rank C)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| skeleton_monster_base | Skeleton | undead | 88 | 19 | 12 | 14 | 14 | 95 |
| skeleton_monster_rusted_sword | Rusted Sword Skeleton | undead | 92 | 20 | 12 | 14 | 13 | 100 |
| zombie_guard_base | Zombie Guard | undead | 96 | 19 | 13 | 13 | 13 | 98 |
| zombie_guard_rusted_sentry | Rusted Sentry | undead | 100 | 19 | 14 | 13 | 12 | 102 |
| zombie_guard_wounded_guard | Wounded Guard | undead | 86 | 18 | 12 | 13 | 13 | 90 |
| zombie_monster_base | Shambler | undead | 90 | 18 | 11 | 13 | 12 | 92 |
| zombie_monster_armed_zombie | Armed Shambler | undead | 95 | 20 | 12 | 13 | 12 | 100 |
| zombie_monster_ragged_worker | Ragged Worker | undead | 80 | 17 | 11 | 12 | 12 | 88 |
| skeleton_archer_base | Skeleton Archer | undead | 84 | 20 | 11 | 14 | 16 | 105 |
| pumpkin_jack_base | Pumpkin Jack | demon | 78 | 24 | 11 | 13 | 18 | 112 |
| bat_demon_red_wing_fiend ◆ | Red Wing Fiend | demon | 90 | 25 | 12 | 15 | 20 | 130 |
| **skeleton_knight_base** ★ | Skeleton Knight | undead | 165 | 27 | 18 | 17 | 14 | 295 |

### Zone 5 — Mountain Foothills (Rank B)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| goblin_bomber_base | Goblin Bomber | humanoid | 105 | 24 | 14 | 12 | 18 | 138 |
| goblin_bomber_redcap_bomber | Redcap Bomber | humanoid | 110 | 25 | 14 | 13 | 19 | 145 |
| goblin_bomber_club_sapper | Club Sapper | humanoid | 120 | 25 | 16 | 12 | 16 | 140 |
| goblin_crossbowman_base | Goblin Crossbowman | humanoid | 102 | 25 | 13 | 12 | 19 | 142 |
| goblin_crossbowman_hooded_marksman | Hooded Marksman | humanoid | 105 | 26 | 13 | 13 | 20 | 152 |
| goblin_crossbowman_knife_backup | Knife Backup | humanoid | 108 | 24 | 14 | 12 | 18 | 138 |
| frankenstein_brawler_base | Frankenstein Brawler | construct | 156 | 24 | 21 | 10 | 14 | 150 |
| frankenstein_brawler_scarred_construct | Scarred Construct | construct | 165 | 25 | 22 | 11 | 14 | 158 |
| pumpkin_jack_lantern_duelist ◆ | Lantern Duelist | demon | 115 | 30 | 14 | 16 | 22 | 168 |
| **titch_the_ticker_171** ★ | Titch the Ticker | construct | 240 | 30 | 28 | 14 | 18 | 380 |

### Zone 6 — Mountain Pass (Rank A)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| orc_raider_base | Orc Raider | humanoid | 145 | 28 | 18 | 15 | 19 | 175 |
| orc_raider_shield_bruiser | Shield Bruiser | humanoid | 158 | 27 | 21 | 15 | 18 | 182 |
| orc_raider_spear_raider | Spear Raider | humanoid | 150 | 30 | 18 | 15 | 20 | 188 |
| orc_archer_base | Orc Archer | humanoid | 138 | 30 | 17 | 16 | 22 | 192 |
| orc_archer_forest_bowman | Forest Bowman | humanoid | 142 | 31 | 17 | 17 | 23 | 198 |
| orc_archer_greatbow_raider | Greatbow Raider | humanoid | 148 | 33 | 18 | 17 | 21 | 205 |
| orc_shaman_base | Orc Shaman | humanoid | 140 | 27 | 17 | 18 | 19 | 200 |
| orc_shaman_bone_caller | Bone Caller | humanoid | 145 | 28 | 17 | 18 | 19 | 208 |
| **orc_shaman_red_hood_shaman** ★ | Red Hood Shaman | humanoid | 285 | 38 | 24 | 28 | 22 | 480 |

### Zone 7 — Sunken Cave (Rank A → S)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| lizard_monster_base | Lizardman | beast | 175 | 32 | 22 | 19 | 22 | 220 |
| lizard_monster_blue_scale_lizard | Blue Scale Lizard | beast | 180 | 32 | 23 | 21 | 23 | 228 |
| lizard_monster_winged_lizard | Winged Lizard | beast | 168 | 35 | 21 | 20 | 25 | 240 |
| pirate_captain_base | Pirate Reaver | humanoid | 178 | 34 | 22 | 19 | 24 | 235 |
| pirate_captain_cutlass_raider | Cutlass Raider | humanoid | 184 | 36 | 22 | 19 | 25 | 248 |
| skeleton_archer_greatbow_bones | Greatbow Bones | undead | 178 | 35 | 21 | 23 | 23 | 245 |
| skeleton_archer_hooded_archer | Hooded Archer | undead | 172 | 34 | 21 | 23 | 23 | 238 |
| skeleton_monster_hooded_bones | Hooded Bones | undead | 185 | 33 | 22 | 25 | 22 | 240 |
| frankenstein_brawler_graveyard_smasher | Graveyard Smasher | construct | 230 | 33 | 30 | 16 | 18 | 252 |
| **pirate_captain_eyepatch_captain** ★ | Eyepatch Captain | humanoid | 360 | 46 | 32 | 28 | 28 | 615 |

### Zone 8 — Corrupted Forest (Rank S)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| dark_fairy_base | Dark Fairy | demon | 215 | 44 | 28 | 26 | 30 | 285 |
| dark_fairy_purple_hex_fairy | Purple Hex Fairy | demon | 220 | 44 | 28 | 27 | 30 | 295 |
| dark_fairy_redcap_fairy | Redcap Fairy | demon | 218 | 45 | 28 | 26 | 32 | 298 |
| pumpkin_jack_harvest_reaper | Harvest Reaper | demon | 230 | 46 | 30 | 27 | 28 | 312 |
| sheep_cultist_base | Sheep Cultist | humanoid | 210 | 38 | 27 | 24 | 25 | 278 |
| sheep_cultist_white_robed_cultist | White Robed Cultist | humanoid | 222 | 39 | 28 | 26 | 25 | 290 |
| sheep_cultist_crystal_cultist | Crystal Cultist | humanoid | 218 | 40 | 28 | 27 | 26 | 302 |
| troll_berserker_base | Troll Berserker | beast | 250 | 42 | 30 | 22 | 24 | 300 |
| troll_berserker_swamp_troll | Swamp Troll | beast | 248 | 41 | 30 | 23 | 24 | 305 |
| troll_shaman_swamp_hexer | Swamp Hexer | beast | 225 | 38 | 27 | 27 | 25 | 318 |
| **troll_shaman_base** ★ | Troll Sage | beast | 460 | 52 | 36 | 38 | 28 | 760 |

### Zone 9 — Volcanic Region (Rank S)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| minotaur_brute_base | Minotaur Brute | beast | 260 | 48 | 33 | 28 | 30 | 340 |
| minotaur_brute_club_brute | Club Brute | beast | 275 | 49 | 35 | 28 | 28 | 350 |
| minotaur_brute_armored_minotaur | Armored Minotaur | beast | 290 | 48 | 38 | 29 | 28 | 365 |
| boarman_berserker_base | Boarman Berserker | beast | 268 | 50 | 33 | 28 | 30 | 358 |
| boarman_berserker_blackhide_raider | Blackhide Raider | beast | 270 | 51 | 33 | 28 | 31 | 368 |
| boarman_berserker_tusk_charger | Tusk Charger | beast | 282 | 52 | 34 | 28 | 30 | 380 |
| pigman_guard_base | Pigman Guard | humanoid | 255 | 43 | 35 | 26 | 28 | 332 |
| pigman_guard_boar_guard | Boar Guard | humanoid | 268 | 44 | 36 | 27 | 28 | 345 |
| pigman_guard_halberd_guard | Halberd Guard | humanoid | 262 | 46 | 35 | 27 | 30 | 358 |
| lizard_dragon_guard_base | Lizard Dragon Guard | beast | 285 | 49 | 36 | 32 | 30 | 380 |
| lizard_dragon_guard_blue_drake_guard | Blue Drake Guard | beast | 290 | 49 | 37 | 33 | 31 | 388 |
| lizard_dragon_guard_trident_guard | Trident Guard | beast | 295 | 51 | 38 | 32 | 32 | 400 |
| **wartotaur_warlord_blackhorn_chief** ★ | Blackhorn Chief | beast | 580 | 62 | 44 | 36 | 30 | 920 |

### Zone 10 — Final Stronghold (Rank SS)
| id | name | type | HP | ATK | DEF | MRES | DEX | EXP |
|---|---|---|---:|---:|---:|---:|---:|---:|
| skeleton_knight_black_knight | Black Knight | undead | 360 | 55 | 44 | 40 | 33 | 425 |
| skeleton_knight_mace_guard | Mace Guard | undead | 372 | 54 | 46 | 39 | 32 | 432 |
| vampire_noble_base | Vampire Noble | demon | 320 | 60 | 40 | 38 | 40 | 442 |
| vampire_noble_masked_vampire | Masked Vampire | demon | 325 | 60 | 40 | 39 | 40 | 448 |
| vampire_noble_blood_court_duelist | Blood Court Duelist | demon | 332 | 62 | 41 | 39 | 41 | 465 |
| vampire_bat_lord_base | Vampire Bat Lord | demon | 310 | 60 | 39 | 38 | 42 | 450 |
| vampire_bat_lord_white_wing_lord | White Wing Lord | demon | 318 | 61 | 39 | 39 | 42 | 458 |
| vampire_bat_lord_blood_saber_lord | Blood Saber Lord | demon | 335 | 63 | 41 | 39 | 42 | 470 |
| troll_berserker_stone_troll | Stone Troll | beast | 380 | 56 | 47 | 36 | 33 | 458 |
| troll_shaman_crystal_sage | Crystal Sage | beast | 340 | 54 | 40 | 41 | 35 | 478 |
| wartotaur_warlord_base | Wartotaur Warlord | beast | 365 | 60 | 46 | 38 | 33 | 485 |
| wartotaur_warlord_bronze_halberdier | Bronze Halberdier | beast | 372 | 61 | 47 | 38 | 34 | 490 |
| fallen_angel_base | Fallen Angel | demon | 322 | 62 | 41 | 40 | 41 | 488 |
| fallen_angel_ash_wing | Ash Wing | demon | 318 | 63 | 41 | 40 | 42 | 495 |
| alien_invader_base | Alien Invader | demon | 328 | 60 | 42 | 41 | 40 | 482 |
| alien_invader_night_alien | Night Alien | demon | 332 | 60 | 42 | 41 | 41 | 488 |
| alien_invader_red_crystal_invader | Red Crystal Invader | demon | 348 | 62 | 43 | 41 | 41 | 505 |
| **fallen_angel_red_judicator** ★ | Red Judicator | demon | 820 | 78 | 56 | 54 | 44 | 1250 |

★ = zone boss · ◆ = barrier (requires `veil_breaker`)

## Boss moveset mapping

The 10 conditional-AI move sets in `data/enemies/boss_move_sets/` were renamed to match the new boss ids; bodies were preserved (they describe phase logic that fits any thematic skin).

| Zone | Boss id (= filename) | Original moveset source |
|---|---|---|
| 1 | grik_the_grin | inline (no `ai_ref`) |
| 2 | wolf_beast_black_fur | mountain_bear.yaml |
| 3 | ratkin_plague_doctor_black_mask_doctor | mud_crab_king.yaml |
| 4 | skeleton_knight_base | forest_spider_giant.yaml |
| 5 | titch_the_ticker_171 | wyvern.yaml |
| 6 | orc_shaman_red_hood_shaman | plague_zombie_ancient.yaml |
| 7 | pirate_captain_eyepatch_captain | frost_dragon.yaml |
| 8 | troll_shaman_base | succubus.yaml |
| 9 | wartotaur_warlord_blackhorn_chief | flame_dragon.yaml |
| 10 | fallen_angel_red_judicator | dullahan.yaml |

`stone_dragon.yaml` had no remaining target boss and was deleted.

## Verification

- `python tools/validate.py --root rusted_kingdoms` → PASS (no broken links, no broken flags).
- `python -m pytest` → 1250 passed.
- Sprite resolution: every enemy id matches a `{id}.tsx` file in `assets/sprites/enemies/`, so battle scenes render real sprites for all 103 entries.
