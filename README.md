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
python -m engine.main --scenario ./rusted_kingdoms
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

```

## Run Data Validation

```sh
source tests/.venv/bin/activate.fish
pip install -e ".[dev]"

cd tests/tools
./validate.py
```

## Issue and Solutions

### Font not found error

```
 in _init_fonts
    self._title_font = pygame.font.SysFont("Arial", 64, bold=True)
                       ^^^^^^^^^^^^^^^^^^^
  File ".../engine/.venv_engine/lib/python3.14/site-packages/pygame/__init__.py", line 70, in __getattr__
    raise NotImplementedError(missing_msg)
NotImplementedError: font module not available (ImportError: cannot import name 'Font' from partially initialized module 'pygame.font'
```

Solution
```sh
# Install font packages
sudo pacman -S sdl2 sdl2_ttf sdl2_image sdl2_mixer
pip uninstall pygame
pip cache purge
pip install -r requirements.txt
```
