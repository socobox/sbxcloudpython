# Find: `select` & `array_type`

Optional request fields on **`POST /api/data/v1/row/find`** and **`POST /api/data/v1/row/find/old`** to shrink payloads and speed up large reads.

Both are **additive**. Omit them and the response matches legacy SBX exactly.

---

## Quick comparison

| Feature | Request field | Default (legacy) | Benefit |
|---------|---------------|------------------|---------|
| Field projection | `select` or `fields` | All model fields per row | Less SQL + smaller JSON when you only need a few columns |
| Response layout | `array_type` | Object array in `results` | Column layout avoids repeating field names on every row |

You can use either feature alone or together.

---

## `select` — field projection

Return only the fields you need. **`_KEY`** and **`_META`** are always included.

### Request

```json
{
  "row_model": "variety",
  "domain": 129,
  "page": 1,
  "size": 250,
  "select": ["variety_name", "inactive"]
}
```

Alias: `"fields": ["variety_name"]` (same as `select`).

### Response (unchanged shape, fewer fields)

```json
{
  "success": true,
  "results": [
    {
      "_KEY": "abc-123",
      "_META": { "created_time": "...", "updated_time": "..." },
      "variety_name": "Rose",
      "inactive": false
    }
  ],
  "model": [
    { "name": "variety_name", "type": "STRING", "..." },
    { "name": "inactive", "type": "BOOLEAN", "..." }
  ],
  "row_count": 42,
  "total_pages": 1
}
```

The `model` array is filtered to match `select`. Pagination, WHERE, sort, and counts behave the same as a full-row find.

### Smart loading

Fields used only for filtering, sorting, or `fetch` are still **loaded internally** but **not returned** unless listed in `select`.

```json
{
  "select": ["inactive"],
  "where": [{ "ANDOR": "AND", "GROUP": [{ "FIELD": "variety_name", "OP": "LIKE", "VAL": "Rose" }] }]
}
```

`variety_name` participates in the WHERE clause; the JSON row only contains `_KEY`, `_META`, and `inactive`.

### `fetch` / `fetched_results`

Forward and reverse fetch still run on full loaded rows. **`fetched_results`** always contains full related records — it is not projected by `select`.

### Rules

- Field names must exist on the model (invalid names → error).
- Do not put `_KEY` or `_META.*` in `select` (they are always returned).
- Omit, `null`, or `[]` → full row (legacy).

---

## `array_type` — response layout

Choose how **`results`** is encoded. Does not change query semantics — same rows, same counts.

### Values

| `array_type` | `results` shape | Notes |
|--------------|-----------------|-------|
| *(omitted)* | `[{ ... }, { ... }]` | Legacy default |
| `"object_array"` | `[{ ... }, { ... }]` | Same rows; response includes `"array_type": "object_array"` |
| `"column_oriented"` | `{ "headers": [...], "data": [[...], ...] }` | Compact for large page sizes |

Alias: `"arrayType"` (camelCase).

### Column-oriented example

**Request:**

```json
{
  "row_model": "variety",
  "domain": 129,
  "page": 1,
  "size": 1000,
  "array_type": "column_oriented",
  "select": ["variety_name", "inactive"]
}
```

**Response:**

```json
{
  "success": true,
  "array_type": "column_oriented",
  "results": {
    "headers": [
      "_KEY",
      "_META.created_time",
      "_META.updated_time",
      "variety_name",
      "inactive"
    ],
    "data": [
      ["abc-123", "2024-01-01T00:00:00.000Z", "2024-01-02T00:00:00.000Z", "Rose", false],
      ["def-456", "2024-01-03T00:00:00.000Z", "2024-01-04T00:00:00.000Z", "Tulip", false]
    ]
  },
  "model": [ "..." ],
  "row_count": 42,
  "total_pages": 1
}
```

System columns always come first: `_KEY`, `_META.created_time`, `_META.updated_time`. With `select`, data columns follow in select order.

Empty pages still return headers (and `"data": []`).

### Why use column-oriented?

On wide models or `size: 1000`, legacy JSON repeats every field name on every row. Column layout sends names once in `headers` and values as arrays — often **much smaller** over the wire and faster to parse in dashboards or ETL pipelines.

Reconstruct a row client-side:

```javascript
function rowAt(col, i) {
  const obj = { _META: {} };
  col.headers.forEach((h, j) => {
    const v = col.data[i][j];
    if (h === "_KEY") obj._KEY = v;
    else if (h === "_META.created_time") obj._META.created_time = v;
    else if (h === "_META.updated_time") obj._META.updated_time = v;
    else obj[h] = v;
  });
  return obj;
}
```

---

## Combined usage

Best for bulk export or analytics UI:

```json
{
  "row_model": "order_line",
  "domain": 129,
  "size": 1000,
  "select": ["order_id", "qty", "status"],
  "array_type": "column_oriented",
  "where": [ "..." ]
}
```

Small payload: only three data columns, no repeated keys in `results`.

---

## Backwards compatibility

| Client sends | Behavior |
|--------------|----------|
| Nothing new | Identical to legacy Node/production SBX |
| `select` only | Same `results` array shape, fewer properties per object |
| `array_type: "column_oriented"` only | New `results` shape + echoed `array_type` |
| Both | Projected columns in chosen layout |

Existing SDKs and apps that omit these fields require **no changes**.

---

## Errors

| Input | Error |
|-------|-------|
| Unknown field in `select` | `{ "success": false, "error": "field_x is not a valid FIELD for the model" }` |
| `_KEY` / `_META.*` in `select` | `{ "success": false, "error": "select cannot include system field: ..." }` |
| Invalid `array_type` | `{ "success": false, "error": "array_type must be \"object_array\" or \"column_oriented\"" }` |

---

## Tests

```bash
bun test tests/array-format.test.ts
bun run test:parity:select          # select + production parity
bun run test:parity:array-format    # array_type + legacy parity
```

**Implementation:** `src/helpers/find-select.ts`, `src/helpers/array-format.ts`, `src/services/data.service.ts`
