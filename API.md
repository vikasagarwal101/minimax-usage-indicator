# MiniMax Token Plan API Reference

API used by this indicator to fetch quota/usage data.

**Base URL:** `https://api.minimax.io`

**Authentication:** Bearer token via `Authorization: Bearer <api_key>` header.

---

## `GET /v1/token_plan/remains`

Returns quota usage and reset information for all models and categories under the authenticated token plan.

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

Each entry represents one model's quota state.

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `model_name` | string | — | Model identifier (e.g. `"MiniMax-M*"`, `"coding-plan-vlm"`) |
| `start_time` | integer | epoch ms | Start of the current interval window |
| `end_time` | integer | epoch ms | End of the current interval window |
| `remains_time` | integer | **milliseconds** | Duration until interval reset (relative to "now") |
| `current_interval_total_count` | integer | requests | Total allowed requests in the current interval |
| `current_interval_usage_count` | integer | requests | Requests used in the current interval |
| `weekly_start_time` | integer | epoch ms | Start of the current weekly cycle |
| `weekly_end_time` | integer | epoch ms | End of the current weekly cycle |
| `weekly_remains_time` | integer | **milliseconds** | Duration until weekly reset (relative to "now") |
| `current_weekly_total_count` | integer | requests/tokens | Total weekly allowance (0 = unlimited) |
| `current_weekly_usage_count` | integer | requests/tokens | Weekly usage so far |

### `category_remains[]` Object

Same fields as `model_remains[]`, plus:

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Category key (e.g. `"text_generation"`, `"video_generation"`) |
| `display_name` | string | Human-readable category name (e.g. `"Text Generation"`) |

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

When `current_weekly_total_count` is `0`, the model has no weekly limit (unlimited weekly usage).

### Model selection

The app selects a primary model by preferring `MiniMax-M*` or any model with `coding-plan` in its name. If none found, it falls back to the first model with a non-zero interval limit.

### Example `remains_time` calculation

```
remains_time = 11293258 (ms)
             = 11293 seconds
             ≈ 3h 8m

reset_at = now_epoch_ms + remains_time
```
