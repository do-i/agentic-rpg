# Map Editor — Usability & Scalability Improvement Plan

High-level suggestions for `tools/map_editor`, covering the two pain points raised:

1. Creating links (portals) between maps is not intuitive.
2. Rendering/interaction performance degrades as nodes and edges grow.

Current scale for reference: **47 maps, 99 portals** in `rusted_kingdoms`. The tool
already shows friction at this size, so the problems are architectural, not data volume.

---

## 1. Why portal-link creation feels unintuitive

The current flow is a hidden, modal, 4-step wizard (`edit/editor_state.py`):

```
[E] enter edit mode → click source node → modal tile picker (source)
                    → click dest node   → modal tile picker (dest)
```

Specific problems:

- **No discoverable affordance.** Edit mode lives behind the `E` key / hamburger
  menu. Nothing on a node or edge suggests "you can connect these."
- **Context is destroyed mid-flow.** Each tile pick opens a full-screen modal, so
  the user can never see both maps at once while making a link. Choosing the
  destination node happens back on the graph, two screens away from where the
  gesture started.
- **The mental model is inverted.** Every mainstream graph editor expresses
  "create edge" as *drag from source to target*. Here it is a memorized command
  sequence with step state (`1/4 … 4/4`) shown only in a HUD corner.
- **Esc is overloaded** (cancel step vs. cancel cycle vs. exit mode), and a
  mis-click silently restarts the cycle.
- **Two-way doors need the whole wizard twice.** Almost every real portal is
  reciprocal (door in ↔ door out), but there is no "create return portal" step.
- **No undo/redo** — only "discard all pending", and save is the `S` key with no
  visible dirty indicator besides the HUD.

### Suggested target interaction (regardless of framework)

- **Drag-to-connect**: press on a source node (or a highlighted portal marker on
  its thumbnail) and drag a rubber-band edge onto the destination node. Drop
  opens *one* small placement popover — not a full-screen modal — to fine-tune
  source/arrival tiles, with both minimaps visible side by side.
- **Portal markers rendered on node thumbnails** at all times (small dots at
  portal tiles). They double as drag handles and make "which tile is the door"
  visible before entering any mode.
- **"Also create return portal" checkbox** in the placement popover, defaulting
  to on, auto-suggesting the reciprocal tile (arrival tile + 1 row below the
  source door — the common convention in the scenario).
- **Edge inspector instead of clipboard-only panel**: selecting an edge should
  let you edit target map/tile in place, not just copy values.
- **Standard editing chrome**: undo/redo stack (the pending-edit model in
  `EditorState` is already 80% of a command stack), Ctrl+S save, visible "3
  unsaved changes" badge, confirm-on-quit when dirty.

---

## 2. Why performance degrades with graph size

All of this is measured against `scenes/graph_scene.py`; the costs are per-frame
Python-interpreter work, so they scale badly even at modest sizes:

- **Everything is recomputed every frame.** `_render_edges` rebuilds riser
  offsets, edge endpoint spreading, and full orthogonal paths for every edge on
  every frame, even when the camera and layout are unchanged.
- **Edge "hop" crossings are quadratic.** `_apply_jumps` tests every horizontal
  segment against every vertical segment of every other edge → O(E²) segment
  checks per frame.
- **Hit-testing rebuilds geometry on every mouse move.** `_edge_at_screen`
  re-routes *all* edges and computes point-to-segment distance per segment on
  each `MOUSEMOTION` event. Mouse movement alone can saturate a core.
- **Thumbnails are rescaled per node per frame.** `pygame.transform.scale` runs
  for every visible node every frame instead of caching a scaled surface per
  zoom level.
- **The spring layout is O(N² × 400 iterations)** at startup
  (`graph/spring_layout.py`). Fine at 47 nodes; minutes-territory at 500.
- **No render caching at all**: the scene redraws at 60 FPS even when idle.

### Short-term fixes if we stay on pygame

Worth doing only if migration (below) is deferred:

1. Cache routed edge paths keyed on `(layout positions, zoom, panel width,
   visibility flags)`; invalidate on drag/zoom/pan, not per frame.
2. Hit-test against the cached paths + a coarse spatial grid; never re-route in
   an event handler.
3. Pre-scale thumbnails into a small mipmap-style cache (e.g. per 0.25× zoom
   bucket).
4. Render the static graph into an offscreen surface; re-blit and only redraw
   overlays (hover, selection, HUD) unless the camera or graph changed.
5. Cap the jump/hop computation with a segment-bucket index instead of the all-
   pairs scan.

These would carry the tool to a few hundred edges, but pygame remains
immediate-mode with no scene graph, no GPU path rendering, no text layout, and
no widget toolkit — every UI feature (panels, modals, scrolling, clipboard) is
hand-rolled, which is exactly why the editor UX lags.

---

## 3. Recommendation: migrate the editor to a web stack

The engine should stay Python/pygame — but the *editor* is a developer tool, and
node-graph editing is a solved problem on the web. Recommended shape:

**Frontend: TypeScript + [React Flow (xyflow)](https://reactflow.dev/)**
(alternatively Svelte Flow — same library family).

- Drag-to-connect edges, connection validation, node drag, pan/zoom, minimap,
  selection, keyboard shortcuts, undo/redo helpers — all built in. The exact
  interaction we struggle to hand-build in pygame is the library's core demo.
- Renders to the DOM/canvas with virtualization; thousands of nodes/edges are
  within its documented comfort zone. If we ever exceed that, Sigma.js
  (WebGL) or Cytoscape.js are drop-in-adjacent alternatives for the view layer.
- Custom node types let us render map thumbnails + portal-tile markers as
  ordinary React components; the tile picker becomes an `<img>` with a click
  overlay instead of a bespoke pygame scene.
- Built-in edge routing (orthogonal/step edges included) replaces
  ~600 lines of Manhattan-routing, riser-lane, and hop-drawing code.

**Backend: keep Python. A thin FastAPI (or stdlib http.server) app that reuses
existing modules:**

- `graph/portal_graph.py` → `GET /graph` (JSON of nodes + edges).
- `edit/tmx_writer.py` (`create_portal`, `save_portal_target`, `delete_portal`)
  → `POST/PATCH/DELETE /portals`. The `.bak` safety behavior carries over as-is.
- Thumbnail generation → `GET /maps/{id}/thumbnail.png` (render once with the
  existing pytmx code, cache to `rusted_kingdoms/.cache/map_editor`).
- Launch remains one command: `python -m tools.map_editor` starts the server and
  opens the browser. No Electron/Tauri needed for a local dev tool; if a native
  window is ever wanted, Tauri can wrap the same frontend later.

Why this beats the alternatives considered:

| Option | Verdict |
| --- | --- |
| Optimize pygame in place | Cheapest, but caps out on UX: every widget stays hand-rolled; drag-to-connect, inspectors, undo UI all remain custom work. |
| Qt (PySide6) `QGraphicsScene` | Stays Python and retained-mode (solves perf), but graph-editor interactions are still DIY, and Qt UI code is heavy to maintain for a side tool. |
| Godot editor plugin / imgui node editors | Powerful but adds a whole new runtime + learning curve for one tool. |
| **Web (React Flow + FastAPI)** | Purpose-built graph-editing UX for free, GPU-accelerated rendering, dev-tools ecosystem (hot reload, inspector). Python I/O layer is preserved untouched. |

The one real cost is introducing a Node/TypeScript toolchain into the repo for
the editor frontend. Scoping it to `tools/map_editor_web/` with its own
`package.json` keeps the engine's Python-only workflow unaffected.

---

## Status (2026-07-15)

Phases 1–3 of the plan below are implemented, plus the editing portion of
phase 3 (originally listed as its own step):

- **Service layer**: `tools/map_editor/service/editor_service.py` wraps graph
  building + TMX mutations, JSON in/out, with unit tests.
- **Backend**: `tools/map_editor/web/server.py` (FastAPI; `pip install -e
  ".[dev,editor]"`) — graph JSON, PNG renders, portal CRUD.
- **Frontend**: `tools/map_editor_web/` (Vite + React + TS + React Flow +
  dagre). Drag-to-connect with side-by-side tile pickers, reciprocal portal
  option, edge retarget/delete, undo/redo. One deliberate deviation from the
  original sketch: edits apply to TMX immediately (with `.bak` backups and
  API-inverse undo) instead of a pending-changes queue — simpler and no less
  safe for a local dev tool.
- **Launch**: `python -m tools.map_editor --web --scenario ./rusted_kingdoms`
  (see `tools/map_editor_web/README.md`).

Remaining: retiring the pygame graph scene once the web editor has proven
itself in day-to-day use (`MapViewScene` stays either way), and the deferred
pygame perf fixes in §2, which are now moot unless the web editor is rejected.

## 4. Suggested phasing

1. **Extract the service layer** (no behavior change): wrap `portal_graph` +
   `tmx_writer` + thumbnail generation behind a small internal API module with
   tests. This is useful even if we never migrate — it decouples editing logic
   from pygame.
2. **Stand up the web editor read-only**: FastAPI serving `/graph` and
   thumbnails; React Flow rendering nodes/edges with layout (use ELKjs or
   dagre instead of porting `spring_layout`). Validate perf and feel.
3. **Port editing**: drag-to-connect → placement popover → PATCH endpoints,
   including "create return portal", undo/redo, dirty indicator, save.
4. **Retire the pygame graph scene** once parity is reached. `MapViewScene`
   (single-map detail view) can migrate last or remain in pygame — it shares
   the sprite/thumbnail cache but little else.
5. Defer the pygame short-term perf fixes (§2) unless phase 2 slips; avoid
   paying for both.
