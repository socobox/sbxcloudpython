# Plan: Add `select`, `array_type`, `_META`/STEP date DSL & `find/old` to the `sbxpy` client (backward-compatible)

> Intended to be executed by **Sonnet**. Read this whole file first, then implement section by section. No test suite exists — see Verification.

## Context

The SBXCloud server gained new **additive** capabilities on `POST /data/v1/row/find` (documented in `docs/FIND-SELECT-AND-ARRAY-TYPE.md` and `docs/DATES-QUERY-DSL.md`):

- **`select` / `fields`** — field projection (shrinks payload; `_KEY` + `_META` always returned).
- **`array_type: "column_oriented"`** — response `results` becomes `{ headers, data }` instead of an object array.
- **`_META.created` / `_META.updated`** — usable in WHERE and in a new `sort: [{field, order}]` array.
- **STEP date DSL** — date values wrapped in `${...}` (e.g. `${last:7d}`, `${this:week}`, `${startOf:day@America/New_York}`) are evaluated server-side; plus an optional `timezone` / `tz` request field.

The Python SDK (`sbxpy/`) supports none of these except passing arbitrary field names in WHERE. The goal is to add them **without breaking compatibility with older servers** that don't understand the new keys.

**Backward-compatibility contract (non-negotiable):**
- New request keys (`select`, `array_type`, `timezone`, `sort`) are emitted **only** when the caller explicitly opts in. A default query must compile to byte-identical JSON as today.
- Old servers ignore unknown request keys and always return the legacy object-array `results`; the client must behave identically in that case.
- STEP `${...}` strings and `_META.*` fields against an old server are the caller's choice (old server treats `${...}` as a literal / may reject `_META.*`); we provide the builders and document the caveat, but never send them implicitly.

**Scope decisions (confirmed with user):**
- Endpoints: add **legacy `find/old`** only. Do **not** add `find/pre` or the `/api/sql/v1/*` endpoints.
- Column-oriented responses: **keep `results` raw** (`{headers, data}`) on the response dict — do **not** transform inside `Find.__then`. Provide a **`to_objects()` helper** (plus a standalone reconstruction function). Accessor methods are made shape-tolerant so they don't become footguns.
- STEP: add a **`Step` builder helper** + a few `_META` convenience WHERE methods.

---

## Changes by file

### 1. `sbxpy/QueryBuilder.py` — new query keys

Add fluent setters (each returns `self`):

```python
def select(self, fields):
    # field projection; alias of server "select"/"fields". Omit/empty -> full row (legacy).
    if fields:
        self.q['select'] = list(fields)
    return self

def set_array_type(self, array_type):
    # "object_array" | "column_oriented"
    self.q['array_type'] = array_type
    return self

def set_timezone(self, tz):
    self.q['timezone'] = tz
    return self

def add_sort(self, field, order="ASC"):
    self.q.setdefault('sort', []).append({"field": field, "order": str(order).upper()})
    return self
```

Update `compile()` so the **insert/rows branch strips the new find-only keys** (defensive — insert builders never set them, but keep `compile()` honest). In the `elif 'rows' in self.q:` block, alongside deleting `where`/`order_by`, also `del` `select`, `array_type`, `timezone`, `sort` if present.

Do **not** change `__init__`'s default `self.q` — defaults stay `{"page": 1, "size": 1000, "where": []}`.

### 2. `sbxpy/__init__.py` — `Find` query methods, `_META` sugar, STEP, `find/old`

**`SbxCore.urls`**: add `'find_old': '/data/v1/row/find'  + '/old'` → i.e. `'/data/v1/row/find/old'`.

**`Find` — new fluent methods** (delegate to `QueryBuilder`, return `self`):
- `select(self, *fields)` — accept either `select("a", "b")` or `select(["a", "b"])`; flatten then call `self.query.select(...)`.
- `set_array_type(self, array_type)`, `column_oriented(self)` → `set_array_type("column_oriented")`, `object_array(self)` → `set_array_type("object_array")`.
- `set_timezone(self, tz)`.
- `sort_by(self, field, order="ASC")` → `self.query.add_sort(...)`. (Keep existing `order_by` untouched — legacy format `{ASC, FIELD}` still works against old servers; `sort_by` is the new array form needed for `_META` sorting.)

**`_META` convenience WHERE methods** on `Find` (thin wrappers over the existing `and_where_*` using the field-name constants — they work today, this is just ergonomics + discoverability). Define module constants:
```python
META_CREATED = "_META.created"
META_UPDATED = "_META.updated"
```
Add e.g. `and_where_created_after(value)`, `and_where_created_before(value)`, `and_where_updated_after(value)`, `and_where_updated_before(value)`, `and_where_created_between(start, end)`, `and_where_updated_between(start, end)` — each delegating to `and_where_greater_or_equal_than` / `and_where_less_or_equal_than` with the constant. `*_between` adds two AND conditions. Values may be literals or `Step.*(...)` strings.

**`find_old(self)`** — mirror of `find()` but POSTs to `urls['find_old']`. Refactor `set_url` (or add a small variant) so `__then` targets the right URL; simplest: add
```python
async def find_old(self):
    self.url = self.sbx_core.urls['find_old']
    return await self.__then(self.query.compile())
```
Leave `find()`, `delete()`, `find_all*` unchanged. **Do not** auto-normalize column responses in `Find.__then` (honors "keep raw").

> Note on `find_all`/`delete` + `column_oriented`: these internal aggregators (`merge_results`, `delete`) assume object-array `results`. Document that `column_oriented` is intended for **single-page raw reads** paired with `to_objects()`. Do not silently break them — leave them as-is, and in the docstring for `column_oriented()`/`set_array_type()` warn that it should not be combined with `find_all()`/`delete()`.

### 3. `sbxpy/timedsl.py` — new module, `Step` builder

Pure string builders producing `${...}` (no network, no deps). Re-export `Step` from the package top-level (`sbxpy/__init__.py`: `from sbxpy.timedsl import Step`) and from `sbxpy/sbx` if convenient.

```python
class Step:
    @staticmethod
    def now(offset=None):        # offset like "-7d", "+2h"
        return f"${{now{offset or ''}}}"
    @staticmethod
    def last(duration):          # "7d", "24:hours", "week"
        return f"${{last:{duration}}}"
    @staticmethod
    def roll(duration):
        return f"${{roll:{duration}}}"
    @staticmethod
    def this(token, tz=None):     # token: day/week/month/quarter/year/monday...
        return Step._wrap(f"this:{token}", tz)
    @staticmethod
    def next(token, tz=None):
        return Step._wrap(f"next:{token}", tz)
    @staticmethod
    def prev(token, tz=None):
        return Step._wrap(f"prev:{token}", tz)
    @staticmethod
    def start_of(token, tz=None):
        return Step._wrap(f"startOf:{token}", tz)
    @staticmethod
    def end_of(token, tz=None):
        return Step._wrap(f"endOf:{token}", tz)
    @staticmethod
    def expr(text, tz=None):      # escape hatch incl. natural language: Step.expr("last 7 days")
        return Step._wrap(text, tz)
    @staticmethod
    def _wrap(body, tz):
        return f"${{{body}{('@' + tz) if tz else ''}}}"
```

(`now`/`last`/`roll` are rolling and never take a timezone per the doc; calendar ops accept optional `tz`.)

### 4. `sbxpy/sbx/__init__.py` — `SBXResponse` column-oriented support

Add a **standalone reconstruction helper** (module-level, also exported), reconstructing rows from `{headers, data}` and **nesting `_META.*` headers** back under a `_META` object (mirrors the JS `rowAt` in the doc):

```python
def column_to_objects(results):
    # results: either a list (legacy) -> returned as-is, or {"headers":[...], "data":[[...]]}
    if not isinstance(results, dict) or "headers" not in results or "data" not in results:
        return results if isinstance(results, list) else []
    headers = results["headers"]
    rows = []
    for row in results["data"]:
        obj = {}
        for h, v in zip(headers, row):
            if h.startswith("_META."):
                obj.setdefault("_META", {})[h[len("_META."):]] = v
            else:
                obj[h] = v
        rows.append(obj)
    return rows
```

**`SBXResponse` changes:**
- Widen the field type: `results: Optional[Union[List[dict], dict]] = None` (accept the column dict without a validation error). Keep raw — no `mode="before"` transform.
- Add `def to_objects(self) -> List[dict]: return column_to_objects(self.results) if self.results is not None else []`.
- Make accessors shape-tolerant by routing through `to_objects()` so they keep working whether `results` is legacy or column:
  - `has_results()` → uses `to_objects()`.
  - `first(type_def)` → `objs = self.to_objects(); return type_def(**objs[0]) if objs else None`.
  - `all(type_def)` → iterate `self.to_objects()`.
- `merge()` stays object-array oriented; add a one-line guard: if any input `results` is a column dict, reconstruct via `column_to_objects` before extending (so merges of mixed/column pages don't crash).

> This satisfies "keep raw + helper": `.results` is never mutated on the response/wire, the helper (`to_objects()` / `column_to_objects`) exists, and the existing `all()/first()` consumers don't become footguns.

### 5. `sbxpy/domain/__init__.py` — expose `_META` on models (small, optional but recommended)

Current line `_META: Optional[MetaModel] = None` is a **pydantic private attribute** (leading underscore) — it is never populated from response data, so model users can't read created/updated times. Add a real, alias-mapped field (keeps `populate_by_name=True` already set):

```python
meta: Optional[MetaModel] = Field(None, alias="_META")
```

Leave the existing `_META` line or remove it (it's dead). This lets `SBXModel` subclasses read `instance.meta.created_time` after a find. Backward compatible (Optional, alias).

---

## Backward-compatibility checklist (verify each)

1. `Find(model, core).query.compile()` with no new methods called → JSON has **only** the legacy keys (`domain`, `row_model`, `page`, `size`, `where`); no `select`/`array_type`/`timezone`/`sort`.
2. A legacy object-array response flows through `SBXResponse.all()/first()` exactly as before.
3. `column_to_objects(legacy_list)` returns the list unchanged; `column_to_objects({headers, data})` reconstructs with nested `_META`.
4. `Step.*` only ever produces strings; nothing is sent unless passed into a WHERE value.
5. `find_old()` hits `/data/v1/row/find/old`; `find()` URL unchanged.

---

## Verification

No suite exists. Add **`tests/`** with offline unit tests (no network) runnable via `uv run pytest` (add `pytest` as a dev dep with `uv add --dev pytest`):

- `test_querybuilder.py`:
  - Default compile has no new keys (compat check #1).
  - `select(["a","b"])`, `set_array_type("column_oriented")`, `set_timezone("America/New_York")`, `add_sort("_META.updated","DESC")` each appear in compiled JSON only when called.
  - Insert builder (`add_object`) compile strips find-only keys.
- `test_column_oriented.py`: `column_to_objects` round-trips the doc's example (incl. `_META.created_time` → `_META.created_time` nested) and passes legacy lists through; `SBXResponse(results={headers,data}).all(Model)` works.
- `test_step.py`: `Step.last("7d") == "${last:7d}"`, `Step.start_of("day","Europe/London") == "${startOf:day@Europe/London}"`, `Step.now("-7d") == "${now-7d}"`, etc.

**Live smoke test** (manual, requires `SBX_DOMAIN/SBX_APP_KEY/SBX_TOKEN/SBX_HOST`): a `uv run` script that:
1. Runs a normal `find()` (baseline, confirms no regression).
2. Runs a `find().select("...").column_oriented()` single-page read and reconstructs via `SBXResponse(**resp).to_objects()`.
3. Runs a `_META.updated >= Step.last("7d")` filter with `sort_by("_META.updated","DESC")`.
4. Runs the same against `find_old()`.

Report results plainly (pass/fail with output). If no live creds, run only the offline pytest suite and say so.

---

## Docs to update after implementation

- `CLAUDE.md`: under "Find", note `select`, `column_oriented`/`to_objects`, `sort_by`, `set_timezone`, `_META` WHERE helpers, `Step` DSL, and the `find/old` endpoint, with the backward-compat note.
- Optionally a short `docs/CLIENT-USAGE.md` with copy-paste examples mirroring the two feature docs.
