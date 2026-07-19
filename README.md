# Agentic RPG Engine

A modular, data-driven JRPG engine built with Python, Pygame, and
[`injector`](https://injector.readthedocs.io/). It is inspired by the compact
worlds, party building, and turn-based battles of the NES and SNES eras.

The repository includes **Chronicles of the Lost Flame**, a work-in-progress
scenario set in the Rusted Kingdoms. Engine code lives in `engine/`; maps,
characters, encounters, dialogue, items, and other scenario content live in
`rusted_kingdoms/`.

## Screenshots

<p align="center">
  <img src="docs/screenshots/title-screen.png" alt="Chronicles of the Lost Flame title screen" width="49%">
  <img src="docs/screenshots/ardel-overworld.png" alt="Ardel overworld with the player, townspeople, shops, and inn" width="49%">
</p>
<p align="center">
  <img src="docs/screenshots/volcanic-battle.png" alt="Five-character party battling two minotaur brutes in a volcanic region" width="49%">
  <img src="docs/screenshots/field-menu.png" alt="Field menu showing status, spells, items, equipment, quests, character, save, and quit commands" width="49%">
</p>

## Highlights

- Tiled/TMX overworlds with collision, portals, NPCs, signs, treasure boxes,
  camera movement, animated sprites, and visible enemy encounters
- Turn-based party combat with front and back rows, abilities, items, status
  effects, enemy AI, bosses, rewards, loot, and animated battle feedback
- Five-member parties with character switching, equipment, spells, shared
  inventory, magic cores, progression, and status screens
- Dialogue-driven quests, shops, inns, crafting at apothecaries, save slots,
  title and game-over flows, audio, and configurable balance data
- Scenario packages made from YAML data and assets instead of story content
  hardcoded into the engine
- Deterministic seeds plus input recording and playback for debugging
- Scenario validation and both web and Pygame map-editing tools

## Requirements

- Python 3.13 or newer
- Git
- Node.js and npm only when using the web map editor

Pygame requires the usual SDL-compatible desktop libraries for your platform.

## Quick Start

```sh
git clone <repository-url>
cd agentic-rpg
./run setup
./run play
```

`./run setup` creates `.venv` and installs the engine, test dependencies, and
web-editor backend in editable mode. To set the environment up manually:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,editor]"
python -m engine.main --scenario ./rusted_kingdoms --seed 1 --mode normal
```

## Controls

| Key | Action |
| --- | --- |
| Arrow keys | Move on the map; navigate menus |
| Enter | Interact; confirm a menu choice |
| `M` | Open or close the field menu |
| `I` | Open items from the overworld |
| `S` | Open character status from the overworld |
| Escape | Go back, close a menu, or attempt to flee in battle |

Menus show additional context-specific controls at the bottom of the screen.

## Commands

The `run` wrapper uses the project virtual environment and keeps the common
workflows in one place:

```sh
./run play                         # play with a deterministic seed
./run record                       # record an input session to recording.pkl
./run replay 2.0                   # replay it at 2x speed
./run test                         # run the full pytest suite
./run test tests/unit/battle       # run a focused test slice
./run validate                     # validate Rusted Kingdoms scenario data
./run map-editor                   # launch the web map editor
./run map-editor-pygame            # launch the legacy Pygame map editor
./run help                         # list every wrapper command
```

The web editor installs its Python extras and builds its frontend on first use
if either is missing.

## Project Layout

```text
engine/                    Reusable engine package, organized by feature
rusted_kingdoms/
  manifest.yaml            Scenario entry point and asset references
  data/                    YAML characters, maps, dialogue, items, and encounters
  assets/                  TMX maps, tilesets, sprites, images, fonts, and audio
tests/                     Unit and integration tests by subsystem
tools/                     Validators, map editors, and content utilities
docs/design/               Long-lived engine and content-system documentation
docs/scenario/             Rusted Kingdoms narrative and world notes
docs/plans/                Active implementation plans
```

The engine uses dependency injection for its runtime services and a scene
registry for title, overworld, battle, dialogue, shop, and menu flows. Feature
packages generally own their scene, state, logic, and renderer together. Start
with the [design index](docs/design/INDEX.md) for deeper subsystem documentation.

## Developing and Validating

Install the editable development environment with `./run setup`, then run:

```sh
./run test
./run validate
```

Pytest is configured to stop on the first failure. The scenario validator
checks manifests and cross-references across maps, encounters, dialogue,
characters, items, portals, and assets. See
[the validation guide](docs/design/validation.md) for its current rules.

## Credits and Attribution

This project uses character sprites and assets from the
[Liberated Pixel Cup collection](https://opengameart.org/content/lpc-collection),
licensed under
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).

Sprite contributors include Johannes Sjölund (wulax), Michael Whitlock
(bigbeargames), Matthew Krohn (makrohn), Nila122, David Conway Jr.
(JaidynReiman), Carlo Enrico Victoria (Nemisys), Thane Brimhall (pennomi),
laetissima, bluecarrot16, Luke Mehl, Benjamin K. Smith (BenCreating),
MuffinElZangano, Durrani, kheftel, Stephen Challener (Redshrike),
William.Thompsonj, Marcel van de Steeg (MadMarcel), TheraHedwig, Evert, Pierre
Vigier (pvigier), Eliza Wyatt (ElizaWy), Sander Frenken (castelonia),
dalonedrau, Lanea Zimmerman (Sharm), Manuel Riecke (MrBeast), Barbara Riviera,
Joe White, Mandi Paugh, Shaun Williams, Daniel Eddeland (daneeklu), Emilio J.
Sanchez-Sierra, drjamgo, gr3yh47, tskaufma, Fabzy, Yamilian, Skorpio, Tuomo
Untinen (reemax), Tracy, thecilekli, LordNeo, Stafford McIntyre, the PlatForge
project, DCSS authors, DarkwallLKE, Charles Sanchez (CharlesGabriel), Radomir
Dopieralski, macmanmatty, Cobra Hubbard (BlueVortexGames), Inboxninja,
kcilds/Rocetti/Eredah, Napsio (Vitruvian Studio), The Foreman, and AntumDeluge.
See the LPC generator's
[full credits](https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator/blob/master/CREDITS.csv)
for detailed attribution.

## License

The engine source is licensed under the MIT License. Bundled third-party assets
remain under their respective licenses and attribution terms.
