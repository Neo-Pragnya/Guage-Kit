---
title: "Errors"
description: "GuageError and the GK-* error codes."
---

# Errors

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

Every expected failure raises `GuageError` with a stable code and a hint; the CLI prints them and exits 2. The codes are listed in the [error reference](../errors.md).

## `guage_kit.errors`

Stable error codes. Every error Guage Kit raises on purpose carries one, so scripts and CI can branch on it.

Add a code here before using it (tests/test_errors.py checks that codes are unique and documented).

### `CODES`

```python
CODES = {'GK-DATA-001': 'dataset file not found', 'GK-DATA-002': 'unsupported dataset format', 'GK-DATA-003': 'invalid sample in dataset', 'GK-DATA-004': 'dataset is empty', 'GK-METRIC-001': 'unknown metric', 'GK-METRIC-002': 'invalid metric parameters', 'GK-METRIC-003': 'metric needs an optional extra that …
```

### `GuageError`

```python
class GuageError(code: str, message: str, *, hint: str | None = None) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/errors.py#L30)

An expected failure with a stable code and a human explanation.
