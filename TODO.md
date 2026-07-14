# TODO

Future sessions should pick one item at a time and keep each change separately
validated and committed.

## P2 - Refactoring candidates

- [ ] Refactor `WorldMapScene` only when touching behavior.
  - Do not split it solely because it is large.
  - If changing overlays, map init, or battle launch, extract that behavior into
    focused helpers as part of that change.
