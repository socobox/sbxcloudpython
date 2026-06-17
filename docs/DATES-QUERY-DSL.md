# Dates Query DSL & `_META` Support

This document describes how **sbx-svc-ts** handles date filtering and sorting in EAV queries, including the **STEP** (SBX Time Expression Protocol) date DSL and pseudo-fields on row metadata.

**Endpoints:** `POST /api/data/v1/row/find`, `POST /api/data/v1/row/find/old`, `GET /api/data/v1/row/find/pre`

**Implementation:** `src/helpers/time-dsl.ts`, `src/helpers/timezone.ts`, `src/services/query-engine.ts`

**Tests:** `tests/time-dsl.test.ts`

---

## Table of contents

1. [Overview](#overview)
2. [Row metadata (`_META`)](#row-metadata-_meta)
3. [Where STEP applies](#where-step-applies)
4. [STEP syntax](#step-syntax)
5. [Operators](#operators)
6. [Period tokens](#period-tokens)
7. [Weekday navigation](#weekday-navigation)
8. [Rolling durations](#rolling-durations)
9. [Natural language phrases](#natural-language-phrases)
10. [Timezone support (STEP v1.1)](#timezone-support-step-v11)
11. [Literals vs expressions](#literals-vs-expressions)
12. [Supported comparison operators](#supported-comparison-operators)
13. [Find request examples](#find-request-examples)
14. [Sorting by `_META`](#sorting-by-_meta)
15. [Response date formats](#response-date-formats)
16. [Errors & validation](#errors--validation)
17. [Quick reference](#quick-reference)

---

## Overview

SBX stores timestamps in **UTC** in MySQL (`row.created`, `row.modification_time`, and `field.date_value` for DATE columns).

When building a WHERE clause, you can pass:

| Value form | Behavior |
|------------|----------|
| Plain string | Used **literally** in SQL (no evaluation) |
| `${...}` | Evaluated by **STEP** at query time, then bound as a MySQL `DATETIME` string (`YYYY-MM-DD HH:mm:ss`) |

STEP is opt-in: only values wrapped in `${...}` are interpreted as expressions. This keeps legacy clients safe — existing literal date strings continue to work unchanged.

**Timezone is also opt-in.** If you do not send `timezone` / `tz` on the find request (and do not use `@IANA` on an expression), calendar operators behave exactly as STEP v1 always has: **UTC boundaries, no timezone logic involved.** You do not need to set `timezone: "UTC"` for default behavior — just omit the field.

Evaluation uses the **server clock** at the moment the find request is processed (not cached across requests).

---

## Row metadata (`_META`)

Every row returned by find includes system metadata alongside user-defined fields:

```json
{
  "_KEY": "550e8400-e29b-41d4-a716-446655440000",
  "_META": {
    "created_time": "2026-06-01T14:30:00.000Z",
    "updated_time": "2026-06-12T09:15:00.000Z"
  },
  "name": "Example",
  "status": "active"
}
```

### Database mapping

| Query / sort field | MySQL column | Response `_META` key |
|--------------------|--------------|----------------------|
| `_META.created` | `row.created` | `created_time` |
| `_META.updated` | `row.modification_time` | `updated_time` |

> **Important:** WHERE and `sort` use `_META.created` / `_META.updated`. The JSON response uses `created_time` / `updated_time` inside the `_META` object. There is no `_META.created` key in the response payload.

If `modification_time` is null, `updated_time` falls back to `created_time` in the response.

### Supported `_META` operations

| Operation | Supported |
|-----------|-----------|
| WHERE filter | Yes — `_META.created`, `_META.updated` |
| ORDER BY | Yes — `sort: [{ "field": "_META.updated", "order": "DESC" }]` |
| SELECT / fetch | N/A — always included in find results |
| Other `_META.*` fields | No — unknown fields raise an error |

`_META` conditions query the `row` table directly (no EAV field JOIN), which makes them efficient for “recently updated rows” filters on large models.

---

## Where STEP applies

STEP evaluation runs when resolving **date values** in WHERE clauses for:

1. **`_META.created`** and **`_META.updated`**
2. Any model field with type **`DATE`**

It does **not** apply to STRING, TEXT, INT, FLOAT, BOOLEAN, or REFERENCE fields unless you pass a literal string.

Timezone context (`timezone` / `tz` on the find body) is **only** read when you explicitly set it. Otherwise the query engine passes an empty context and STEP uses the legacy UTC calendar path — same results as before timezone support existed.

---

## STEP syntax

```
${ expression }
${ expression @ IANA_TIMEZONE }
```

### Grammar

```
expression := keyword
            | keyword : token
            | now [ ± duration ]
            | last : duration
            | last : calendar_period
            | natural_language_phrase

keyword   := now | startOf | endOf | this | next | prev | last | roll
token     := period | weekday
duration  := <number><unit>  |  <number>:<long_unit>
unit      := s | m | h | d | w
long_unit := second(s) | minute(s) | hour(s) | day(s) | week(s)
period    := day | week | month | quarter | year | yesterday | today
weekday   := monday … sunday  (aliases: mon, tue, wed, thu, fri, sat, sun)
```

### Wrapper rules

| Input | Result |
|-------|--------|
| `${last:7d}` | Evaluated |
| `last:7d` | **Literal string** `"last:7d"` |
| `now-7d` | **Literal string** (no wrapper) |
| `${now}` | Current server time |
| `${}` | Error — empty wrapper |

Whitespace inside the wrapper is trimmed. Natural phrases like `last 7 days` are normalized before parsing.

---

## Operators

| Operator | Meaning | Example | Notes |
|----------|---------|---------|-------|
| `now` | Evaluation instant | `${now}` | Same as server UTC “now” |
| `startOf` | Start of containing period (00:00:00) | `${startOf:month}` | Calendar boundary |
| `endOf` | End of containing period (23:59:59) | `${endOf:week}` | Calendar boundary |
| `this` | Alias for `startOf` | `${this:quarter}` | Readable in filters |
| `next` | Start of the **following** period | `${next:monday}` | Strictly after base; on Monday → +7 days |
| `prev` | Start of the **previous** period | `${prev:week}` | Calendar boundary |
| `last` | Rolling lookback **or** calendar shortcut | `${last:7d}`, `${last:week}` | See [Rolling durations](#rolling-durations) |
| `roll` | Alias for rolling `last` | `${roll:24h}` | Same as `${last:24h}` |

### Calendar semantics (default: UTC)

- **Weeks** use ISO weeks: **Monday 00:00 → Sunday 23:59:59**
- **Quarters** are calendar quarters (Jan–Mar, Apr–Jun, …)
- **`yesterday`** is its own period token (not the same as `prev:day` when crossing month boundaries in edge cases — prefer explicit tokens in tests)
- **`today`** normalizes to `this:day`

---

## Period tokens

| Token | Aliases | `this:` (start) | `endOf:` |
|-------|---------|-----------------|----------|
| Day | `day`, `today` | Today 00:00 | Today 23:59:59 |
| Yesterday | `yesterday` | Yesterday 00:00 | Yesterday 23:59:59 |
| Week | `week` | Monday 00:00 of current week | Sunday 23:59:59 |
| Month | `month` | 1st 00:00 | Last day 23:59:59 |
| Quarter | `quarter`, `q` | 1st of quarter 00:00 | Last day of quarter 23:59:59 |
| Year | `year` | Jan 1 00:00 | Dec 31 23:59:59 |

### Examples (UTC, base = Friday 2026-06-12 12:00:00)

| Expression | Resolves to (MySQL DATETIME, UTC) |
|------------|-----------------------------------|
| `${this:day}` | `2026-06-12 00:00:00` |
| `${prev:day}` | `2026-06-11 00:00:00` |
| `${next:day}` | `2026-06-13 00:00:00` |
| `${this:week}` | `2026-06-08 00:00:00` |
| `${prev:week}` | `2026-06-01 00:00:00` |
| `${next:week}` | `2026-06-15 00:00:00` |
| `${endOf:week}` | `2026-06-14 23:59:59` |
| `${this:month}` | `2026-06-01 00:00:00` |
| `${prev:month}` | `2026-05-01 00:00:00` |
| `${startOf:quarter}` | `2026-04-01 00:00:00` |
| `${endOf:quarter}` | `2026-06-30 23:59:59` |
| `${prev:quarter}` | `2026-01-01 00:00:00` |

---

## Weekday navigation

Weekday tokens: `monday` … `sunday` (short: `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`).

| Expression | Meaning (UTC) |
|------------|---------------|
| `${this:monday}` | Monday 00:00 of the week containing base |
| `${next:monday}` | Next Monday 00:00 (if base is Monday, +7 days) |
| `${prev:monday}` | Previous Monday 00:00 (7 days before this week's Monday) |
| `${endOf:friday}` | Friday 23:59:59 of the week anchored by `this:friday` |

### Examples (base = Friday 2026-06-12 12:00 UTC)

| Expression | Resolves to |
|------------|-------------|
| `${this:monday}` | `2026-06-08 00:00:00` |
| `${next:monday}` | `2026-06-15 00:00:00` |
| `${prev:monday}` | `2026-06-01 00:00:00` |
| `${next:fri}` | `2026-06-19 00:00:00` |
| `${endOf:friday}` | `2026-06-12 23:59:59` |

---

## Rolling durations

Rolling expressions subtract time from **`now`** (absolute UTC offset). They do **not** snap to calendar boundaries and are **not** affected by timezone settings.

### Short form

```
${now-7d}          → now minus 7 days
${now+2h}          → now plus 2 hours
${last:7d}         → same as now-7d
${roll:24h}        → alias for last:24h
```

Units: `s` (seconds), `m` (minutes), `h` (hours), `d` (days), `w` (weeks).

### Long form (after `last:` or `roll:`)

```
${last:7:days}
${last:24:hours}
${last:1:weeks}
```

### Calendar shortcuts via `last:`

| Expression | Meaning |
|------------|---------|
| `${last:hour}` | Now minus 1 hour (rolling) |
| `${last:day}` | Start of previous calendar day (`prev:day`) |
| `${last:week}` | Start of previous calendar week (`prev:week`) |
| `${last:month}` | Start of previous calendar month |
| `${last:quarter}` | Start of previous calendar quarter |
| `${last:year}` | Start of previous calendar year |

---

## Natural language phrases

These work **inside** `${...}` (spaces are normalized):

| Phrase | Canonical |
|--------|-----------|
| `last week` | `prev:week` |
| `last month` | `prev:month` |
| `last quarter` | `prev:quarter` |
| `last year` | `prev:year` |
| `this week` | `this:week` |
| `this month` | `this:month` |
| `this quarter` | `this:quarter` |
| `this year` | `this:year` |
| `last day` | `prev:day` |
| `last hour` | `last:1h` |
| `last 7 days` | `last:7d` |
| `last 24 hours` | `last:24h` |
| `last 30 days` | `last:30d` |
| `last 1 week` | `last:1w` |
| `today` | `this:day` |
| `yesterday` | `prev:day` |
| `next monday` | `next:monday` |
| `previous friday` | `prev:friday` |
| `this monday` | `this:monday` |

Legacy camel shorthands (`lastweek`, `thismonth`, …) are also accepted.

Example:

```json
{ "VAL": "${last 7 days}" }
```

---

## Timezone support (STEP v1.1, optional)

> **Default: no timezone.** Omit `timezone` / `tz` on the request and omit `@IANA` on expressions. Everything works in UTC exactly as before — no timezone field required, no implicit conversion.

Use timezone **only** when you intentionally want calendar boundaries in a specific IANA region (e.g. “start of today in New York”). Database timestamps remain UTC; non-UTC boundaries are converted to a UTC instant for SQL comparison.

Rolling offsets (`last:7d`, `now-24h`) never use timezone — absolute UTC math from `now`.

### Request-level (opt-in)

Pass `timezone` or `tz` on the find body (or query string for `GET /find/pre`):

```json
{
  "row_model": "cart_box",
  "timezone": "America/New_York",
  "where": [
    {
      "ANDOR": "AND",
      "GROUP": [
        {
          "ANDOR": "AND",
          "FIELD": "_META.updated",
          "OP": ">=",
          "VAL": "${startOf:day}"
        }
      ]
    }
  ]
}
```

At `2026-06-12 12:00 UTC` (08:00 EDT), `${startOf:day}` with `America/New_York` resolves to **`2026-06-12 04:00:00`** UTC (midnight EDT).

**Without `timezone`:** `${startOf:day}` → `2026-06-12 00:00:00` UTC (legacy behavior). Do not add a timezone field unless you need local calendar boundaries.

Explicit `timezone: "UTC"` or `@UTC` on an expression is equivalent to omitting timezone entirely.

### Per-expression override

Append `@IANA` inside the wrapper (overrides request default):

```
${startOf:day@Europe/London}
${next:monday@America/New_York}
${this:week@UTC}
```

Request uses `America/New_York`, expression uses London:

```json
{
  "timezone": "America/New_York",
  "where": [{ "GROUP": [{ "FIELD": "_META.updated", "OP": ">=", "VAL": "${startOf:day@Europe/London}" }] }]
}
```

### Valid timezone values

Any IANA name accepted by `Intl.DateTimeFormat` (e.g. `America/New_York`, `Europe/London`, `UTC`, `GMT`).

Invalid values return HTTP 200 with `{ "success": false, "error": "Invalid IANA timezone: ..." }`.

---

## Literals vs expressions

| VAL in WHERE | Treated as |
|--------------|------------|
| `"2026-06-01 00:00:00"` | Literal |
| `"2026-06-01T00:00:00.000Z"` | Normalized to `2026-06-01 00:00:00` (ISO `T` / `.000Z` stripped) |
| `"next:monday"` | Literal (no `${}` wrapper) |
| `"${next:monday}"` | STEP expression |
| `"now-7d"` | Literal |
| `"${now-7d}"` | STEP expression |

Use literals when you need an exact fixed timestamp. Use STEP when the boundary should move with query execution time.

---

## Supported comparison operators

All standard SBX WHERE operators work on date / `_META` fields:

| Operator | Example |
|----------|---------|
| `=`, `!=`, `<>` | Exact match / inequality |
| `>`, `<`, `>=`, `<=` | Range filters (most common with STEP) |
| `IS NULL`, `IS NOT NULL` | Null checks (no `VAL` placeholder) |

Example range for “updated this calendar week (UTC)”:

```json
{
  "FIELD": "_META.updated",
  "OP": ">=",
  "VAL": "${this:week}"
}
```

Combine with `endOf` in another clause for an inclusive week window:

```json
[
  { "ANDOR": "AND", "FIELD": "_META.updated", "OP": ">=", "VAL": "${this:week}" },
  { "ANDOR": "AND", "FIELD": "_META.updated", "OP": "<=", "VAL": "${endOf:week}" }
]
```

---

## Find request examples

### Rows updated in the last 7 days

```json
POST /api/data/v1/row/find
{
  "row_model": "cart_box",
  "page": 1,
  "size": 250,
  "where": [
    {
      "ANDOR": "AND",
      "GROUP": [
        {
          "ANDOR": "AND",
          "FIELD": "_META.updated",
          "OP": ">=",
          "VAL": "${last:7d}"
        }
      ]
    }
  ]
}
```

### Rows created since start of today (New York)

```json
{
  "row_model": "order",
  "timezone": "America/New_York",
  "where": [
    {
      "ANDOR": "AND",
      "GROUP": [
        {
          "ANDOR": "AND",
          "FIELD": "_META.created",
          "OP": ">=",
          "VAL": "${startOf:day}"
        }
      ]
    }
  ]
}
```

### DATE field with STEP

```json
{
  "row_model": "event",
  "where": [
    {
      "ANDOR": "AND",
      "GROUP": [
        {
          "ANDOR": "AND",
          "FIELD": "scheduled_at",
          "OP": ">=",
          "VAL": "${next:monday}"
        }
      ]
    }
  ]
}
```

### Mixed `_META` and model fields

```json
{
  "row_model": "cart_box",
  "timezone": "America/New_York",
  "where": [
    {
      "ANDOR": "AND",
      "GROUP": [
        {
          "ANDOR": "AND",
          "FIELD": "_META.updated",
          "OP": ">=",
          "VAL": "${this:week}"
        },
        {
          "ANDOR": "AND",
          "FIELD": "status",
          "OP": "=",
          "VAL": "active"
        }
      ]
    }
  ],
  "sort": [
    { "field": "_META.updated", "order": "DESC" }
  ]
}
```

### GET find/pre (public preview endpoint)

```
GET /api/data/v1/row/find/pre?row_model=cart_box&timezone=America/New_York&where=[...]
```

Query params: `domain`, `row_model`, `page`, `size`, `where` (JSON string), `timezone` or `tz`.

---

## Sorting by `_META`

```json
{
  "row_model": "cart_box",
  "sort": [
    { "field": "_META.updated", "order": "DESC" },
    { "field": "_META.created", "order": "ASC" }
  ]
}
```

Sort uses the same `_META.created` / `_META.updated` field names as WHERE. Multiple sort fields are supported; `_KEY` is also sortable.

---

## Response date formats

| Context | Format | Example |
|---------|--------|---------|
| STEP → SQL binding | MySQL DATETIME (UTC) | `2026-06-12 04:00:00` |
| `_META` in find results | Legacy ISO UTC | `2026-06-12T09:15:00.000Z` |
| DATE fields in find results | Legacy ISO UTC | `2026-06-12T09:15:00.000Z` |

Response dates always use the legacy SBX format: `yyyy-MM-ddTHH:mm:ss.000Z` (milliseconds fixed to `.000`).

---

## Errors & validation

| Condition | Error |
|-----------|-------|
| Invalid STEP syntax | `Invalid time expression "…". STEP v1: ${now}, ${last:7d}, …` |
| Empty `${}` | `Time DSL wrapper ${} cannot be empty` |
| Invalid IANA timezone | `Invalid IANA timezone: Not/AZone` |
| Unknown `_META` field | `Unknown _META field: _META.foo` |
| Invalid operator | `Invalid operator: …` |

All errors return HTTP **200** with `{ "success": false, "error": "…" }` (legacy SBX contract).

---

## Quick reference

### Enable STEP

Wrap the expression: **`${...}`**

### Set timezone (only when needed)

```json
{ "timezone": "America/New_York" }
```

or per expression: **`${startOf:day@Europe/London}`**

Omit both for standard UTC STEP behavior.

### Filter recently updated rows

```json
{ "FIELD": "_META.updated", "OP": ">=", "VAL": "${last:7d}" }
```

### Filter “today” in a timezone

```json
{
  "timezone": "America/Los_Angeles",
  "where": [{ "GROUP": [{ "FIELD": "_META.updated", "OP": ">=", "VAL": "${startOf:day}" }] }]
}
```

### Operator cheat sheet

```
${now}                    Current time
${now-7d}                 Rolling 7 days ago
${last:7d}                Same as now-7d
${this:week}              Start of current week
${prev:month}             Start of previous month
${next:monday}            Next Monday 00:00
${endOf:quarter}          End of current quarter
${last week}              Natural language → prev:week
${startOf:day@UTC}        Per-expression timezone
```

### Exported constants (for tooling)

From `src/helpers/time-dsl.ts`:

- `STEP_OPERATORS` — `now`, `startOf`, `endOf`, `this`, `next`, `prev`, `last`, `roll`
- `STEP_PERIOD_TOKENS` — `day`, `week`, `month`, `quarter`, `year`
- `STEP_WEEKDAY_TOKENS` — full weekday names
- `timeDslGrammarSummary()` — one-line grammar hint string

---

## Related reading

- [CLAUDE.md](../CLAUDE.md) — architecture, pagination, EAV model
- [README.md](../README.md) — setup and API overview
- `tests/time-dsl.test.ts` — executable specification for STEP behavior
