---
name: coding-guidelines
description: >-
  Coding standards, engineering workflow, and communication protocols for this repository.
  Use whenever planning, designing, writing, reviewing, or testing code, or when interacting
  with the user regarding project implementation.
---

# Coding Guidelines & Engineering Standards

This skill defines the coding style, implementation workflow, and communication protocols for developing and maintaining code in this repository.

---

## 1. Core Philosophy: Simple & Human-Readable Code

- **Simplicity First**: Always strive towards writing simple, clean code that is easy for humans to read, understand, and maintain.
- **Avoid Over-Engineering**: Prefer straightforward, direct implementations over clever tricks or unnecessary abstractions.
- **Minimal Inline Comments**: Keep inline comments to a minimum. The code structure, naming, and typing should be self-explanatory. Only add inline comments when non-obvious business logic, mathematical formulas, or edge-case rationales genuinely require clarification.

---

## 2. Interaction & Alignment Protocols

### "question:" Prompts
- If the user begins a prompt with `question:` (or `Question:`), **only answer the question**.
- **Do not write, edit, or execute code changes** when a prompt starts with `question:`.

### Pre-Implementation Alignment (Larger Tasks)
- For larger tasks or architectural changes, always propose implementation ideas in the form of clear questions to align with the user before writing code.
- Smaller tasks or straightforward bug fixes do not require prior questioning; proceed directly with the solution.

### Constructive Pushback & Critical Feedback
- Actively evaluate the user's suggestions and design proposals.
- If a proposed idea is suboptimal, flawed, or if a better alternative exists:
  1. Proactively push back before writing any code.
  2. Clearly explain why the idea may be problematic or where trade-offs lie.
  3. Offer better, simpler alternatives.

---

## 3. Function & Class Signature Standards

- **Explicit Type Hints**: All function parameters, class attributes, and return values must be explicitly typed using standard Python type annotations (e.g. `typing` and `collections.abc`).
- **No `**kwargs`**: Do not use `**kwargs` unless strictly necessary (e.g., mandated by an external library interface). All supported arguments must be declared explicitly in the function/class signature.
- **No Implicit Values**: Avoid hidden defaults or implicit behaviors. Parameters must be explicit and predictable.
- **Single Argument Name**: Every argument to a function or class must have exactly one clean, canonical name. Avoid aliases, duplicate arguments, or multiple parameter variations for the same concept.
- **No Function Aliases**: Functions should never have aliases (e.g., do not define convenience aliases like `generate_table = generate_latex_table` or `load_wandb_metrics = fetch_wandb_metrics`). Every function and class must have exactly one canonical name.

---

## 4. Documentation Standards

- **User-Facing Docstrings**: Write thorough docstrings for all public modules, classes, methods, and functions that are exposed to the user.
- **Docstring Structure**: Clearly document the summary, `Parameters` (with types and descriptions), and `Returns` (or `Raises` where applicable), adhering to the existing docstring conventions in the codebase.

---

## 5. Testing Guidelines

- **Fast Execution**: Tests must run quickly. Use mocks for network services, external APIs (e.g. WandB), and slow I/O.
- **Focused & Balanced**: Write tests covering critical paths, edge cases, and regression risks, but do not overdo them with redundant tests.
