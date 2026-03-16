# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`sbxpy` is a Python SDK for the SBXCloud BaaS (Backend as a Service) platform. It provides async HTTP clients (via aiohttp) for CRUD operations, querying, event handling, workflow management, and optional Redis caching. Published to PyPI as `sbxpy`.

## Build & Development

- **Package manager**: uv
- **Python**: >= 3.12 (pyproject.toml) / >= 3.13 (README target)
- **Install dependencies**: `uv sync`
- **Add dependency**: `uv add <package>`
- **Run a script**: `uv run <script.py>`
- **Build package**: `python setup.py sdist bdist_wheel`
- **No test suite exists** — test manually via scripts with env vars configured

## Environment Variables

Required for SBXCloud connection:
- `SBX_DOMAIN` — domain ID
- `SBX_APP_KEY` — application key
- `SBX_TOKEN` — auth token
- `SBX_HOST` — base URL (e.g., `https://sbxcloud.com/api`)

Optional for Redis caching:
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_USER`, `REDIS_PASSWORD`

## Architecture

All library code lives in `sbxpy/`. The `build/` directory contains stale build artifacts.

### `sbxpy/__init__.py` — Core module (majority of the library)

Contains multiple client classes, each following the same pattern: initialize with domain/credentials, build queries, execute async HTTP requests via aiohttp.

- **`SbxCore`** — Main SBXCloud client. Handles auth, CRUD (`upsert`, `login`), cloudscript management (`run`, `create_cloudscript`, `list_cloudscripts`, `get_cloudscript`, `update_cloudscript`), model/field management (`create_model`, `create_field`, `list_domain`), and creates `Find` query objects via `with_model()`.
- **`Find`** — Fluent query builder for find/delete operations. Supports `and_where_*`/`or_where_*` conditions, `fetch_models` (JOINs), pagination, `find_all()` with concurrent page fetching via semaphore-limited `asyncio.gather`.
- **`SbxEvent` / `EventQuery`** — Client for the SBXCloud event service (separate base URL, uses `sbx-secret` header).
- **`SbxWorkflow` / `WorkflowQuery`** — Client for workflow/process execution API.
- **`SbxCRMUser` / `UserQuery`** — Client for CRM user management API.
- **`ReferenceJoin` / `FilterJoin`** — Reference join query helpers.

### `sbxpy/QueryBuilder.py`

Low-level query JSON builder. Constructs the `where`, `rows`, `fetch`, `order_by`, and `page`/`size` parameters sent to the SBXCloud API.

### `sbxpy/domain/__init__.py`

- **`SBXModel`** — Pydantic BaseModel base class for all domain models. Maps `_KEY` to `key` field. Hashable by key.
- **`@sbx(model="name")`** — Decorator that binds a model class to an SBXCloud model name (stored as `cls._model`).
- **`MetaModel`** — Timestamps sub-model (`created_time`, `updated_time`).

### `sbxpy/sbx/__init__.py`

- **`SBX`** — Singleton accessor for `SbxCore`, reads credentials from env vars.
- **`SBXService`** — Abstract base with `find()`, `get_by_key()`, `list_all()` convenience methods.
- **`SBXResponse`** — Pydantic model wrapping API responses. Key methods: `all(Type)`, `first(Type)`, `get_ref(model, key, Type)`, `merge()`, `has_results()`.

### `sbxpy/cache/__init__.py`

- **`RedisService`** — Async Redis client (via `redis.asyncio`) for caching Pydantic objects as JSON. Supports get/set/mget/mset with optional TTL, plus key index management.

### `sbxpy/service/__init__.py`

- **`SBXCachedService`** — Extends `SBXService` with Redis cache-through pattern for `get()` and `list()` operations.

## API Endpoints Used

### Data
- `POST /data/v1/row` — insert records
- `POST /data/v1/row/update` — update records
- `POST /data/v1/row/find` — query records
- `POST /data/v1/row/delete` — delete records

### Models & Fields
- `GET /data/v1/row/model/list?domain={id}` — list models (`list_domain()`)
- `POST /data/v1/row/model?domain={id}&name={name}` — create model (`create_model()`)
- `POST /data/v1/field/model?domain={id}&name={name}&row_model_id={id}&type={type}` — create field (`create_field()`). Field types: `STRING`, `INT`, `FLOAT`, `BOOLEAN`, `TEXT`, `REFERENCE`. For `REFERENCE`, pass `reference_type=target_model_id`.

### CloudScripts
- `POST /cloudscript/v1/run` — execute a cloudscript (`run()`)
- `POST /cloudscript/v1.5/{domain_id}` — create cloudscript (`create_cloudscript()`)
- `GET /cloudscript/v1.5/{domain_id}?page=N` — list cloudscripts (`list_cloudscripts()`)
- `GET /cloudscript/v1.5/{domain_id}/{key}` — get cloudscript (`get_cloudscript()`)
- `PUT /cloudscript/v1.5/{domain_id}/{key}/script` — update cloudscript (`update_cloudscript()`)

## Key Conventions

- All API calls are async (use `await`). The library uses `aiohttp.ClientSession` per request.
- `upsert()` separates items with `_KEY` (updates) from those without (inserts) and sends them to different endpoints (`/data/v1/row/update` vs `/data/v1/row`).
- Maximum 1000 records per upsert call.
- `find_all()` fetches the first page, reads `total_pages`, then fetches remaining pages concurrently with semaphore-limited parallelism (default 2).
- Dates in SBXCloud are often stored as `int` in `YYYYMMDD` format.
- Domain models use Pydantic v2 with `populate_by_name=True` to handle the `_KEY` alias.
