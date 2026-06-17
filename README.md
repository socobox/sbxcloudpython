# sbxcloudpython

Python library for **SBXCloud**. Minimum Python version is **3.12**. It uses `asyncio`
coroutines for concurrency and `aiohttp` for HTTP requests.

This release adds the new server-side find features — **field projection (`select`)**,
**sort arrays**, **`_META` (created/updated) queries & sorting**, **timezone-aware
date filtering with the STEP DSL**, and an optional **column-oriented response layout** —
**without breaking compatibility with older servers**. Everything new is *opt-in*: if you
don't call the new methods, requests are identical to before and run unchanged against an
old server (see [Backward compatibility](#backward-compatibility)).

---

# SBXCloud Project

## Project Setup

- Package manager: **uv**
- Python: >= 3.12
- Run: `uv run main.py`
- Install deps: `uv sync`
- Add dep: `uv add <package>`
- Run tests: `uv run pytest`

## Environment Variables (.env)

```
SBX_DOMAIN=<domain_id>       # Domain ID in SBXCloud
SBX_APP_KEY=<app_key>        # Application key for authentication
SBX_TOKEN=<token>            # Auth token
SBX_HOST=https://sbxcloud.com/api   # Base URL of the SBXCloud API
```

> `SBX.get_instance()` reads `SBX_DOMAIN`, `SBX_APP_KEY`, `SBX_TOKEN` and `SBX_HOST`.

---

## SBXCloud Platform Overview

SBXCloud is a BaaS (Backend as a Service) platform that allows creating **models**
(equivalent to database tables) within **domains** (equivalent to databases/projects).
Each domain has an `APP_KEY` for identification and a `TOKEN` for authentication.

### Core Concepts

- **Domain**: A project/workspace that contains models. Identified by `DOMAIN` ID.
- **Model**: Equivalent to a database table. Has a name and contains records.
- **Record**: Each record automatically gets a `_KEY` field (primary key, auto-generated on insert) and `_META` (creation/update timestamps).
- **Fetch Models**: Equivalent to JOINs - resolve references to other models.

---

## sbxpy Library Usage

### Initialization

```python
from sbxpy import SbxCore
from sbxpy.sbx import SBX, SBXResponse
from dotenv import load_dotenv

load_dotenv()
sbx: SbxCore = SBX.get_instance()
```

`SBX.get_instance()` reads `SBX_DOMAIN`, `SBX_APP_KEY`, `SBX_TOKEN`, `SBX_HOST` from environment.

### Defining Models

Models extend `SBXModel` and use the `@sbx(model="model_name")` decorator. The `model_name` must match the model name in SBXCloud.

```python
from typing import Optional, List
from pydantic import BaseModel
from sbxpy.domain import SBXModel, sbx

@sbx(model="category")
class SBXCategory(SBXModel):
    category: str

@sbx(model="color")
class SBXColor(SBXModel):
    color_name: str
    html_code_1: Optional[str] = None
    color_group: Optional[str] = None
```

**Key rules for models:**
- All models inherit from `SBXModel` (which provides `key` mapped to `_KEY`, and `meta` mapped to `_META`).
- Use the `@sbx(model="model_name")` decorator to bind to a SBXCloud model.
- Fields use Python type hints. Use `Optional[type] = None` for nullable fields.
- References to other models are stored as `str` (the `_KEY` of the referenced record).
- You can type a reference field as `Optional[ModelClass]` when it will be populated via `fetch_models`.

Read row metadata after a find via the `meta` field:

```python
item = response.first(SBXColor)
print(item.meta.created_time, item.meta.updated_time)   # both Optional[datetime]
```

---

## Using the library with an OLD server

If your SBXCloud server does **not** have the new find features, use the library exactly as
before. Do **not** call `select()`, `sort_by()`, `column_oriented()`, `set_timezone()`, the
`_META` where-helpers, or pass STEP `${...}` values — none of those keys are sent unless you
opt in.

### Basic Query

```python
sbx: SbxCore = SBX.get_instance()
query = sbx.with_model("model_name")
response = SBXResponse(**await query.find())
items = response.all(SBXModelClass)   # Returns List[SBXModelClass]
```

### Find All (paginated automatically)

```python
response = SBXResponse(**await query.find_all())
```

`find()` returns a single page. `find_all()` iterates all pages automatically.

### Where Clauses

```python
# Filter by specific keys
query = sbx.with_model("variety").where_with_keys(["key1", "key2", "key3"])

# Greater or equal than
query = (sbx.with_model("cart_box_item")
         .and_where_greater_or_equal_than("cart_box.packing_date", "20260131"))

# Other where methods (follow the pattern):
# .and_where_is_equal(field, value)
# .and_where_is_not_equal(field, value)
# .and_where_less_than(field, value)
# .and_where_greater_than(field, value)
# .and_where_less_or_equal_than(field, value)
# .and_where_is_not_null(field)
# .and_where_is_null(field)
# .and_where_contains/starts_with/ends_with(field, value)
# .and_where_in/not_in(field, list)
# or_where_* variants and new_group_with_and()/new_group_with_or() for grouping
```

### Sorting (legacy)

```python
# legacy order_by -> {"ASC": bool, "FIELD": name}; works on every server
query = sbx.with_model("variety").order_by("variety_name", asc=True)
```

### Fetch Models (JOINs)

Resolve references to other models in a single query. Pass a list of model field names or nested paths.

```python
query = (sbx.with_model("variety")
         .where_with_keys(variety_keys)
         .fetch_models(["product_group", "product_group.category"]))

response = SBXResponse(**await query.find())

# Access fetched/joined data:
# response.fetched_results["product_group"][key_value] -> dict of the referenced record
# response.fetched_results["category"][key_value]      -> dict of nested reference
```

**Nested fetch**: `"product_group.category"` means: from the `product_group` reference, also
fetch its `category` reference. The fetched results are stored flat by model name in
`response.fetched_results`.

---

## Using the library with the NEW server

The new server supports additive find features. All of them are opt-in via fluent methods and
fall back gracefully: an old server simply ignores the extra request keys and returns the
legacy response. See [Backward compatibility](#backward-compatibility) for the exact contract.

### 1. `select` — field projection

Return only the fields you need (smaller payloads). `_KEY` and `_META` are always returned.

```python
# both forms accepted
query = sbx.with_model("variety").select("variety_name", "inactive")
query = sbx.with_model("variety").select(["variety_name", "inactive"])

response = SBXResponse(**await query.find())
items = response.all(SBXVariety)   # only projected fields are populated
```

### 2. `sort_by` + `_META` sorting

`sort_by()` emits the new `sort: [{field, order}]` array (multiple sort fields allowed). This
is required to sort by metadata. Legacy `order_by()` is left untouched.

```python
query = (sbx.with_model("cart_box")
         .sort_by("_META.updated", "DESC")
         .sort_by("_META.created", "ASC"))
```

### 3. Querying by `_META.created` / `_META.updated`

Use the `_META` constants directly with any where-method, or the convenience helpers. WHERE
uses `_META.created` / `_META.updated`; the response nests them under `_META` as
`created_time` / `updated_time`.

```python
from sbxpy import META_UPDATED   # == "_META.updated"  (also META_CREATED)

# explicit field name with any where-method
query = sbx.with_model("cart_box").and_where_greater_or_equal_than(META_UPDATED, "2026-06-01 00:00:00")

# convenience helpers
query = sbx.with_model("cart_box").and_where_updated_after("2026-06-01 00:00:00")
query = sbx.with_model("order").and_where_created_between("2026-01-01 00:00:00",
                                                          "2026-03-31 23:59:59")
```

### 4. Timezone + STEP date DSL

Date values wrapped in `${...}` (STEP expressions) are evaluated **server-side** at query
time. Build them with `Step`. `set_timezone()` adds an optional IANA timezone for calendar
boundaries; rolling offsets (`Step.last`, `Step.now`) never use a timezone.

```python
from sbxpy import Step

# "rows updated in the last 7 days", newest first
query = (sbx.with_model("cart_box")
         .and_where_updated_after(Step.last("7d"))
         .sort_by("_META.updated", "DESC"))

# "created since start of today in New York"
query = (sbx.with_model("order")
         .set_timezone("America/New_York")
         .and_where_created_after(Step.start_of("day")))

# Step builders:
Step.now()                              # "${now}"
Step.now("-7d")                         # "${now-7d}"
Step.last("7d")                         # "${last:7d}"
Step.this("week")                       # "${this:week}"
Step.prev("month")                      # "${prev:month}"
Step.next("monday")                     # "${next:monday}"
Step.start_of("day", tz="Europe/London")# "${startOf:day@Europe/London}"
Step.end_of("quarter")                  # "${endOf:quarter}"
Step.expr("last 7 days")                # "${last 7 days}"  (natural language)
```

> A STEP `${...}` value sent to an **old** server is treated as a *literal* string (it won't
> match), and `_META.*` fields may be rejected. Only use STEP / `_META` when targeting a server
> that supports them — the library never injects them implicitly.

### 5. Column-oriented response (optional)

For wide models or large pages, request a compact `{headers, data}` layout instead of an array
of objects. The `results` on the response stays **raw**; use `to_objects()` (or the typed
`all()` / `first()`) to reconstruct rows — they work with either layout.

```python
query = (sbx.with_model("variety")
         .set_page_size(1000)
         .select("variety_name", "inactive")
         .column_oriented())

resp = await query.find()
# resp["results"] is { "headers": [...], "data": [[...], ...] }  (compact over the wire)

response = SBXResponse(**resp)
rows  = response.to_objects()       # list[dict], _META.* nested back under "_META"
items = response.all(SBXVariety)    # typed objects, same as object-array mode
```

`find_all()` works with `column_oriented()` too: every page is fetched column-oriented and the
**merged result stays column-oriented** (one `headers` + all pages' `data` concatenated). The
library never converts implicitly — if you want rows, convert **explicitly** with
`to_objects()` / `all()` / `first()` (or the standalone `column_to_objects()`):

```python
resp = await sbx.with_model("variety").column_oriented().find_all()
# resp["results"] is { "headers": [...], "data": [...] }  -> all pages, still compact

response = SBXResponse(**resp)
items = response.all(SBXVariety)     # explicit conversion to typed objects
rows  = response.to_objects()        # explicit conversion to list[dict]
```

`delete()` also accepts `column_oriented()` (it extracts the keys internally regardless of
layout).

### 6. Legacy `find/old` endpoint

`find_old()` posts the same query to `/data/v1/row/find/old` (server's legacy default page
size). Same builder, different endpoint.

```python
response = SBXResponse(**await sbx.with_model("variety").find_old())
```

### Putting it together

```python
from sbxpy import SbxCore, Step
from sbxpy.sbx import SBX, SBXResponse

sbx: SbxCore = SBX.get_instance()

query = (sbx.with_model("order_line")
         .select("order_id", "qty", "status")        # field projection
         .and_where_is_equal("status", "active")
         .and_where_updated_after(Step.last("30d"))   # STEP + _META filter
         .set_timezone("America/New_York")            # timezone for calendar boundaries
         .sort_by("_META.updated", "DESC")            # sort by metadata
         .set_page_size(1000)
         .column_oriented())                          # compact wire payload

response = SBXResponse(**await query.find())
lines = response.all(SBXOrderLine)
```

---

## Backward compatibility

The new features were designed so that **the same library works against old and new servers**:

| You call… | Old server | New server |
|-----------|------------|------------|
| Nothing new | Identical to previous releases | Identical legacy behavior |
| `select(...)` | Key ignored → full rows returned | Projected fields |
| `column_oriented()` | Key ignored → object array; `to_objects()` is a no-op | `{headers, data}`; `to_objects()`/`all()`/`first()` reconstruct (works with `find_all()`/`delete()` too) |
| `sort_by(...)` | New `sort` key may be ignored (use `order_by` for old) | Multi-field sort incl. `_META` |
| `set_timezone(...)` / `Step.*` | `timezone` ignored; `${...}` treated literally | Evaluated server-side |
| `_META.*` filters | May be rejected by old server | Supported in WHERE/sort |

Contract details:

- New request keys (`select`, `array_type`, `timezone`, `sort`) are emitted **only** when you
  call their setters. A default query compiles byte-identically to previous releases.
- The response `results` is never mutated on the wire; column reconstruction is on demand via
  `SBXResponse.to_objects()` / `all()` / `first()` and is a no-op for legacy object arrays.
- STEP `${...}` and `_META.*` are caller choices for new servers; nothing is injected implicitly.

---

### Insert / Update (Upsert)

The `upsert` function handles both inserts and updates in a single call:

```python
sbx: SbxCore = SBX.get_instance()

# Insert new records (no _KEY field)
result = await sbx.upsert("model_name", [
    {"field1": "value1", "field2": "value2"},
    {"field1": "value3", "field2": "value4"},
])
# result contains "keys" array with the new _KEY values in the same order

# Update existing records (include _KEY field)
await sbx.upsert("model_name", [
    {"_KEY": "existing_key_1", "field1": "new_value"},
    {"_KEY": "existing_key_2", "field2": "new_value"},
])

# Mixed insert + update in one call
await sbx.upsert("model_name", [
    {"field1": "new_record"},               # Will INSERT (no _KEY)
    {"_KEY": "abc123", "field1": "updated"} # Will UPDATE (has _KEY)
])
```

**Important upsert rules:**
- **Limit**: Maximum **1000 records per upsert** call. Batch larger sets.
- **Insert detection**: Records **without** `_KEY` are inserted.
- **Update detection**: Records **with** `_KEY` are updated.
- **Response on insert**: The response includes a `"keys"` array with the new `_KEY` values in the **same order** as the input records.
- Only send fields you want to update; unchanged fields don't need to be included.

### Delete

```python
# delete by explicit keys
await sbx.with_model("model_name").where_with_keys(["k1", "k2"]).delete()

# delete by query (finds matching keys first, then deletes)
await sbx.with_model("model_name").and_where_is_equal("status", "obsolete").delete()
```

### Models & Fields Management

You can list existing models, create new models, and add fields (attributes) to them programmatically.

#### List Models

```python
sbx: SbxCore = SBX.get_instance()

# Returns the list of models in the domain
result = await sbx.list_domain()
models = result.get("items", [])
for model in models:
    print(model["name"], model["id"], model.get("properties", []))
```

#### Create a Model

```python
# Create a new model (table) in the domain
result = await sbx.create_model("my_new_model")
model_id = result["row_model"]["id"]
```

#### Create Fields (Attributes)

```python
# Add a STRING field
await sbx.create_field(model_id, "name", "STRING")

# Add an INT field
await sbx.create_field(model_id, "quantity", "INT")

# Add a FLOAT field
await sbx.create_field(model_id, "price", "FLOAT")

# Add a BOOLEAN field
await sbx.create_field(model_id, "active", "BOOLEAN")

# Add a TEXT field
await sbx.create_field(model_id, "description", "TEXT")

# Add a REFERENCE field (foreign key to another model)
await sbx.create_field(model_id, "category", "REFERENCE", reference_type=other_model_id)
```

**Available field types:** `STRING`, `INT`, `FLOAT`, `BOOLEAN`, `TEXT`, `REFERENCE`.

---

### CloudScripts

CloudScripts are server-side JavaScript functions that run on SBXCloud. You can create, list, get, update, and execute them.

#### Execute a CloudScript

```python
sbx: SbxCore = SBX.get_instance()

# Run a cloudscript by key with parameters
result = await sbx.run("cloudscript_key", {"param1": "value1", "param2": "value2"})
```

#### Create a CloudScript

```python
result = await sbx.create_cloudscript("my_script", '{"key": "value"}')
# result contains the created cloudscript info
```

#### List CloudScripts

```python
# List cloudscripts (paginated, default page=1)
result = await sbx.list_cloudscripts(page=1)
```

#### Get a CloudScript by Key

```python
result = await sbx.get_cloudscript("cloudscript_key")
```

#### Update a CloudScript

```python
# Update the script code and optionally a test script
result = await sbx.update_cloudscript(
    "cloudscript_key",
    script='console.log("hello world")',
    test_script='console.log("test")'
)
```

---

### SBXResponse

```python
response = SBXResponse(**await query.find())

# Works for both object-array and column-oriented layouts:
items: list[SBXModelClass] = response.all(SBXModelClass)   # typed list
first: SBXModelClass | None = response.first(SBXModelClass) # first row or None
rows: list[dict]            = response.to_objects()         # raw rows as dicts
has: bool                   = response.has_results()

# Access fetched (joined) model data
fetched_data = response.fetched_results["model_name"]  # dict[str, dict]
# Key is the _KEY of the fetched record, value is a dict of its fields

# Reference helper
ref = response.get_ref("product_group", some_key, SBXProductGroup)

# Merge several raw page responses (tolerates mixed/column layouts)
merged = SBXResponse.merge([page1, page2, page3])
```

---

## Common Patterns

### Grouping items by reference key

```python
items_by_ref: dict[str, list[ItemClass]] = {}
for item in items:
    if item.ref_key not in items_by_ref:
        items_by_ref[item.ref_key] = []
    items_by_ref[item.ref_key].append(item)
```

### Batching upserts (>1000 records)

```python
BATCH_SIZE = 1000
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i + BATCH_SIZE]
    await sbx.upsert("model_name", batch)
```

### Date format

Stored DATE/numeric dates in SBXCloud are often `int` in `YYYYMMDD` format (e.g., `20260131`).

```python
from datetime import datetime

def date_to_number_date(d: datetime) -> int:
    return int(d.strftime("%Y%m%d"))
```

For `_META` / DATE filtering on the new server, prefer literal MySQL datetimes
(`"2026-06-01 00:00:00"`) or moving STEP expressions (`Step.last("7d")`, `Step.this("week")`).
See `docs/DATES-QUERY-DSL.md` and `docs/FIND-SELECT-AND-ARRAY-TYPE.md` for the full server spec.
