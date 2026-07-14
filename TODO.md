# TODO

Future sessions should pick one item at a time and keep each change separately
validated and committed.

## P2 - Refactoring candidates

- [ ] Refactor `WorldMapScene` only when touching behavior.
  - Do not split it solely because it is large.
  - If changing overlays, map init, or battle launch, extract that behavior into
    focused helpers as part of that change.

## P3 - Test and packaging hygiene

## P4 - Small batchable cleanup

- [ ] Rename `grik_the_grin_192` assets/ids if the sheet is standard 64 px tiles.
  - Update the boss id/reference and generated battle sheet references together.
