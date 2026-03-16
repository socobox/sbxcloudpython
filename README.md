# sbxcloudpython

This is the first version of Python Library for SbxCloud. The min Python version require is 3.13, this library depends on courutines with asyncio in order to use concurrent task, and uses aiohttp to do the request. You can test using the test.py file, before execute it, configuring your credentials in the environment.


/cl# SBXCloud Project

## Project Setup

- Package manager: **uv**
- Python: >= 3.13.1
- Run: `uv run main.py`
- Install deps: `uv sync`
- Add dep: `uv add <package>`

## Environment Variables (.env)

```
SBX_DOMAIN=<domain_id>       # Domain ID in SBXCloud
SBX_APP_KEY=<app_key>        # Application key for authentication
SBX_TOKEN=<token>            # Auth token
SBX_BASE_URL=https://sbxcloud.com/api
```

---

## SBXCloud Platform Overview

SBXCloud is a BaaS (Backend as a Service) platform that allows creating **models** (equivalent to database tables) within **domains** (equivalent to databases/projects). Each domain has an `APP_KEY` for identification and a `TOKEN` for authentication.

### Core Concepts

- **Domain**: A project/workspace that contains models. Identified by `DOMAIN` ID.
- **Model**: Equivalent to a database table. Has a name and contains records.
- **Record**: Each record automatically gets a `_KEY` field (primary key, auto-generated on insert).
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

`SBX.get_instance()` reads `SBX_DOMAIN`, `SBX_APP_KEY`, `SBX_TOKEN` from environment.

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
- All models inherit from `SBXModel` (which provides `key` field mapped to `_KEY`).
- Use the `@sbx(model="model_name")` decorator to bind to a SBXCloud model.
- Fields use Python type hints. Use `Optional[type] = None` for nullable fields.
- References to other models are stored as `str` (the `_KEY` of the referenced record).
- You can type a reference field as `Optional[ModelClass]` when it will be populated via `fetch_models`.

### Querying Data

#### Basic Query

```python
sbx: SbxCore = SBX.get_instance()
query = sbx.with_model("model_name")
response = SBXResponse(**await query.find())
items = response.all(SBXModelClass)  # Returns List[SBXModelClass]
```

#### Find All (paginated automatically)

```python
response = SBXResponse(**await query.find_all())
```

`find()` returns a single page. `find_all()` iterates all pages automatically.

#### Where Clauses

```python
# Filter by specific keys
query = sbx.with_model("variety").where_with_keys(["key1", "key2", "key3"])

# Greater or equal than
query = sbx.with_model("cart_box_item").and_where_greater_or_equal_than("cart_box.packing_date", "20260131")

# Other where methods (follow the pattern):
# .and_where_equal_to(field, value)
# .and_where_not_equal_to(field, value)
# .and_where_less_than(field, value)
# .and_where_greater_than(field, value)
# .and_where_less_or_equal_than(field, value)
# .and_where_is_not_null(field)
# .and_where_is_null(field)
```

#### Fetch Models (JOINs)

Resolve references to other models in a single query. Pass a list of model field names or nested paths.

```python
query = (sbx.with_model("variety")
         .where_with_keys(variety_keys)
         .fetch_models(["product_group", "product_group.category"]))

response = SBXResponse(**await query.find())

# Access fetched/joined data:
# response.fetched_results["product_group"][key_value] -> dict of the referenced record
# response.fetched_results["category"][key_value] -> dict of nested reference
```

**Nested fetch**: `"product_group.category"` means: from the `product_group` reference, also fetch its `category` reference. The fetched results are stored flat by model name in `response.fetched_results`.

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
    {"field1": "new_record"},              # Will INSERT (no _KEY)
    {"_KEY": "abc123", "field1": "updated"} # Will UPDATE (has _KEY)
])
```

**Important upsert rules:**
- **Limit**: Maximum **1000 records per upsert** call. Batch larger sets.
- **Insert detection**: Records **without** `_KEY` are inserted.
- **Update detection**: Records **with** `_KEY` are updated.
- **Response on insert**: The response includes a `"keys"` array with the new `_KEY` values in the **same order** as the input records.
- Only send fields you want to update; unchanged fields don't need to be included.

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

# Get typed list of results
items: list[SBXModelClass] = response.all(SBXModelClass)

# Access fetched (joined) model data
fetched_data = response.fetched_results["model_name"]  # dict[str, dict]
# Key is the _KEY of the fetched record, value is a dict of its fields
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

Dates in SBXCloud are often stored as `int` in `YYYYMMDD` format (e.g., `20260131`).

```python
from datetime import datetime

def date_to_number_date(d: datetime) -> int:
    return int(d.strftime("%Y%m%d"))
```
