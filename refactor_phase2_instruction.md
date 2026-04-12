# Split Large Files into Consistent Chunks

**Task:** Create a plan to split large Python modules into smaller, consistently named files while preserving behavior.

## Goal

Reduce file size and improve readability by separating code into focused modules with predictable naming.

## File Naming Convention

Use descriptive prefixes based on feature and responsibility:

```
<feature>_<role>.py
<feature>_<subdomain>_<role>.py
```

Examples:

```
battle_logic.py
battle_damage_logic.py
battle_targeting_logic.py
battle_status_logic.py

shop_logic.py
shop_pricing_logic.py
shop_inventory_logic.py
```

## Standard Roles

Use consistent module purposes:

| role           | responsibility          |
| -------------- | ----------------------- |
| logic          | core rules and behavior |
| renderer       | UI or output formatting |
| state          | state containers        |
| data           | immutable configuration |
| constants      | enums, fixed values     |

## Splitting Heuristics

Split when:

* file exceeds ~350 lines (soft guideline)
* multiple independent responsibilities exist
* sections can be grouped by subdomain
* functions operate on different entity types
* cognitive load is high when navigating file

Do NOT split when:

* logic is tightly coupled
* separation would increase circular imports
* resulting files would be trivial in size

## Deliverables

1. Proposed file breakdown for each large module
2. Naming plan for resulting files
3. Dependency considerations
4. Import update examples
5. Order of operations for safe refactor

## Constraints

* Preserve behavior
* Minimize circular imports
* Prefer shallow hierarchies
* Maintain consistent naming patterns

