# Contributing to ADLAS

Thank you for your interest in contributing to ADLAS. This document outlines the technical workflow and code quality guidelines for all contributors.

---

## 1. Code of Conduct and Professional Standards

- Maintain an academic, professional engineering style in all code, comments, documentation, and commit messages.
- Emoticon and informal icon usage is strictly prohibited across the repository.
- Avoid committing secrets, credentials, temporary files, or unquantized binary models.

---

## 2. Branching Strategy

The repository follows a trunk-based integration workflow:
- `main`: Production-ready, stable codebase used for official release tagging. Direct pushes are prohibited.
- `develop`: Integration branch for active features.
- Feature branches: Created from `develop` following the naming convention:
  `feat/tv<member-number>-<feature-name>` or `fix/tv<member-number>-<bug-name>`

Example:
```bash
git checkout develop
git pull origin develop
git checkout -b feat/tv2-socratic-dialog-engine
```

---

## 3. Commit Guidelines

All commits must follow the Conventional Commits specification:
```text
<type>(<scope>): <concise description in imperative mood>
```

Types:
- `feat`: A new user-facing or technical capability.
- `fix`: A bug fix.
- `docs`: Documentation changes only.
- `refactor`: Code restructuring without modifying functionality.
- `perf`: Performance improvements.
- `test`: Adding or updating test cases.
- `infra`: Infrastructure, Docker, or build tooling changes.

Scopes:
- `identity`, `course`, `learning`, `assessment`, `exam`, `gradebook`, `analytics`, `gateway`, `db`.

Example:
```text
feat(exam): implement monotonic sequence verification for autosave
```

---

## 4. File Headers and Open Source Compliance

Every newly created source file (`.py`, `.ts`, `.tsx`, `.sql`, `.sh`) must include standard copyright and SPDX license identifier headers at the top:

```python
# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT
```

---

## 5. Pull Request Process

1. Ensure all linting and test suites pass locally prior to submitting a pull request.
2. Link the pull request to the corresponding issue or functional specification.
3. Every pull request targeting `develop` requires approval from at least one peer reviewer.
