# TODO give title

## Virtual Environment

```sh
cd $project_root
python -m venv .venv
source .venv/bin/activate.fish
pip install .
```

## Run Game

```sh
cd $project_root
source .venv/bin/activate.fish
python -m engine.main --scenario ./rusted_kingdoms  --seed 1

# 2× faster
python -m engine.main --scenario ./rusted_kingdoms  --seed 1 --mode playback --recording-file session.pkl --playback-speed
2.0

# half speed
python -m engine.main --scenario ./rusted_kingdoms  --seed 1 --mode playback --recording-file session.pkl --playback-speed
0.5

```

## Run Unit Test


```sh
cd $project_root
source .venv/bin/activate.fish
pip install -e ".[dev]"

# Run all tests
python -m pytest

# Run a specific file
python -m pytest tests/unit/core/state/test_map_state.py

# Run a specific class
python -m pytest tests/unit/core/state/test_map_state.py::TestMoveTo

# Run a specific test
python -m pytest tests/unit/core/state/test_map_state.py::TestMoveTo::test_updates_current_and_position

# Suppress warning
PYTHONWARNINGS="ignore::RuntimeWarning" python -m pytest

```

## Run Data Validation

```sh
source tests/.venv/bin/activate.fish
pip install -e ".[dev]"

cd tests/tools
./validate.py
```
## Credits and Attribution

This project uses character sprites and assets from the Liberated Pixel Cup (LPC) collection.

*   **Sprites by:** Johannes Sjölund (wulax), Michael Whitlock (bigbeargames), Matthew Krohn (makrohn), Nila122, David Conway Jr. (JaidynReiman), Carlo Enrico Victoria (Nemisys), Thane Brimhall (pennomi), laetissima, bluecarrot16, Luke Mehl, Benjamin K. Smith (BenCreating), MuffinElZangano, Durrani, kheftel, Stephen Challener (Redshrike), William.Thompsonj, Marcel van de Steeg (MadMarcel), TheraHedwig, Evert, Pierre Vigier (pvigier), Eliza Wyatt (ElizaWy), Johannes Sjölund (wulax), Sander Frenken (castelonia), dalonedrau, Lanea Zimmerman (Sharm), Manuel Riecke (MrBeast), Barbara Riviera, Joe White, Mandi Paugh, Shaun Williams, Daniel Eddeland (daneeklu), Emilio J. Sanchez-Sierra, drjamgo, gr3yh47, tskaufma, Fabzy, Yamilian, Skorpio, kheftel, Tuomo Untinen (reemax), Tracy, thecilekli, LordNeo, Stafford McIntyre, PlatForge project, DCSS authors, DarkwallLKE, Charles Sanchez (CharlesGabriel), Radomir Dopieralski, macmanmatty, Cobra Hubbard (BlueVortexGames), Inboxninja, kcilds/Rocetti/Eredah, Napsio (Vitruvian Studio), The Foreman, AntumDeluge [1].
*   **Source Project:** Sprites were contributed as part of the Liberated Pixel Cup project from OpenGameArt.org: http://opengameart.org/content/lpc-collection [1].
*   **License:** Creative Commons Attribution-ShareAlike 3.0 (CC-BY-SA 3.0) http://creativecommons.org/licenses/by-sa/3.0/ [1].
*   **Detailed Credits:** [https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator/blob/master/CREDITS.csv](https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator/blob/master/CREDITS.csv)
