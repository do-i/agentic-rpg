# Map Editor — Web Frontend

React Flow UI for browsing and editing the scenario's portal graph. The
Python backend (`tools/map_editor/web/server.py`) owns all TMX reading and
writing; this app is presentation only.

## One-time build

```sh
cd tools/map_editor_web
npm install
npm run build          # outputs dist/, served by the Python backend at "/"
```

## Run

```sh
./run map-editor                 # provisions extras + frontend build on first run
```

or manually:

```sh
pip install -e ".[dev,editor]"   # once, for fastapi/uvicorn
python -m tools.map_editor --web --scenario ./rusted_kingdoms
```

## Frontend development

```sh
python -m tools.map_editor --web --scenario ./rusted_kingdoms --no-browser &
npm run dev            # Vite dev server on :5173, proxies /api to :8017
```

## Using the editor

- **Create a portal**: drag the green dot on a map's right edge onto another
  map. Pick the door tile and the arrival tile in the dialog; leave "also
  create return portal" checked for a two-way door.
- **Edit a portal**: click its edge, then "Move arrival tile…" or "Delete
  portal" in the right panel.
- **Undo / redo**: Ctrl+Z / Ctrl+Shift+Z (or the toolbar buttons).
- Edits write to the TMX files immediately; the first edit per file creates a
  sibling `.bak` backup.
