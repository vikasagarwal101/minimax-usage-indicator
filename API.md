# MiniMax Token Plan API Reference

API used by this indicator to fetch quota/usage data.

**Base URL:** `https://api.minimax.io`

**Authentication:** Bearer token via `Authorization: Bearer <api_key>` header.

---

## `GET /v1/api/openplatform/coding_plan/remains`

> This is the canonical path used by the official `MiniMax-AI/cli` and is what this indicator calls. The legacy `GET /v1/token_plan/remains` route returns an identical payload.

Returns quota usage and reset information for all quota buckets under the authenticated token plan.

### Request

```
GET /v1/token_plan/remains
Authorization: Bearer sk-cp-...
Accept-Language: en-US,en
Content-Type: application/json
```

No query parameters required.

### Response

```json
{
  "model_remains": [ ... ],
  "category_remains": [ ... ],
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `model_remains` | array | Per-model quota entries (see below) |
| `category_remains` | array | Per-category quota entries (see below) |
| `base_resp` | object | API status: `status_code` 0 = success |

### `model_remains[]` Object

Each entry represents one quota bucket. Buckets are not request-time model IDs (those are things like `MiniMax-M2.7` or `coding-plan-vlm`); they are aggregated quota categories. The two known values are `general` (combined text/speech/image/music quota) and `video` (separate video quota).

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `model_name` | string | — | Quota bucket: `"general"` or `"video"`. Not a plan or model identifier. |
| `start_time` | integer | epoch ms | Start of the current interval window |
| `end_time` | integer | epoch ms | End of the current interval window |
| `remains_time` | integer | **milliseconds** | Duration until interval reset (relative to "now") |
| `current_interval_total_count` | integer | requests | Total allowed requests in the current interval. Often `0` when the server does not expose raw counts — see `current_interval_remaining_percent` as the reliable signal in that case. |
| `current_interval_usage_count` | integer | requests | Requests used in the current interval. Often `0` when the server does not expose raw counts. |
| `current_interval_remaining_percent` | integer | 0–100 | Server-computed remaining percent for the interval window. Preferred display value. |
| `current_interval_status` | integer | enum | Whether the bucket is enabled on the current subscription. Observed values: `1` = enabled, `3` = not enabled on this plan. Enum is not officially documented. |
| `weekly_start_time` | integer | epoch ms | Start of the current weekly cycle |
| `weekly_end_time` | integer | epoch ms | End of the current weekly cycle |
| `weekly_remains_time` | integer | **milliseconds** | Duration until weekly reset (relative to "now") |
| `current_weekly_total_count` | integer | requests | Total weekly allowance. `0` does **not** mean "unlimited" — it means the count is not exposed; use the percent field instead. Weekly tracking is being rolled out and may be absent on some plans. |
| `current_weekly_usage_count` | integer | requests | Weekly usage so far. Often `0` when the server does not expose raw counts. |
| `current_weekly_remaining_percent` | integer | 0–100 | Server-computed remaining percent for the weekly window. May be absent while the weekly feature is being enabled. |
| `current_weekly_status` | integer | enum | Same shape as `current_interval_status`. |

### `category_remains[]` Object

Same fields as `model_remains[]`, plus:

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Category key (e.g. `"text_generation"`, `"video_generation"`) |
| `display_name` | string | Human-readable category name (e.g. `"Text Generation"`) |

> `category_remains` is documented here but has not been observed in live responses for Token Plan subscribers; it may apply to other subscription tiers.

### `base_resp` Error Codes

| `status_code` | Meaning |
|----------------|---------|
| `0` | Success |
| `1004` | Authentication error |
| `1011` | Authentication error |
| `1024` | Authentication error |

HTTP 401/403 also indicate invalid or expired API keys.

---

## Important Notes

### Time units

- **`start_time`**, **`end_time`**, **`weekly_start_time`**, **`weekly_end_time`** are absolute timestamps in **epoch milliseconds**.
- **`remains_time`** and **`weekly_remains_time`** are **durations in milliseconds** (not epoch timestamps). To compute the absolute reset time: `reset_epoch_ms = current_time_ms + remains_time`.

### Interval window

The interval window is typically a 5-hour rolling window. The `start_time` and `end_time` fields define the current active window.

### Weekly quotas

Weekly data is exposed on the same endpoint via the `*_weekly_*` fields. There is no separate weekly endpoint. When `current_weekly_total_count == 0` and `current_weekly_remaining_percent` is also absent, weekly tracking is not enabled for the current subscription. The legacy interpretation "`total == 0` means unlimited" no longer holds — the percent field is the source of truth when present.

### Model selection

The app selects a primary bucket by preferring the `"general"` bucket when `current_interval_status == 1`, then any bucket with `status == 1`, then the first bucket in the list. The old `MiniMax-M*` / `coding-plan` name match is obsolete — those are request-time model IDs, not values returned by `/remains`.

### Example `remains_time` calculation

```
remains_time = 11293258 (ms)
             = 11293 seconds
             ≈ 3h 8m

reset_at = now_epoch_ms + remains_time
```

### Reading the percent fields

The `*_remaining_percent` fields are server-computed and should be preferred over deriving percent from `usage_count / total_count` whenever they are present. On plans where the server does not expose raw counts (so `total_count == 0` and `usage_count == 0`), the percent field is the only signal.

To display "used percent" (the value shown in the panel label), compute `100 - *_remaining_percent`. To display "remaining percent" (used in progress bars as a fraction remaining), use the field directly.
