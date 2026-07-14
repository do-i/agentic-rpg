# TODO

Future sessions should pick one item at a time and keep each change separately
validated and committed.

## P2 - Refactoring candidates

- [ ] Clean up `ItemScene` modal handling.
  - Keep behavior unchanged.
  - Replace the long modal dispatch chain with a small explicit modal-state
    dispatcher.
  - Preserve current action, discard, AOE confirm, tag editing, manage, and
    target overlay flows.

- [ ] Refactor `WorldMapScene` only when touching behavior.
  - Do not split it solely because it is large.
  - If changing overlays, map init, or battle launch, extract that behavior into
    focused helpers as part of that change.

## P3 - Test and packaging hygiene

- [ ] Reorganize unit tests to mirror engine package layout.
  - Move tests mechanically with `git mv`.
  - Avoid content changes in the move commit.
  - Follow with separate commits for any missing coverage.

## P4 - Small batchable cleanup

- [ ] Rename `grik_the_grin_192` assets/ids if the sheet is standard 64 px tiles.
  - Update the boss id/reference and generated battle sheet references together.
