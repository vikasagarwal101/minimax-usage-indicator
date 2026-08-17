import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

API_BASE = "https://api.minimax.io"
# Canonical path used by the official MiniMax-AI/cli; same payload as the
# legacy /v1/token_plan/remains route.
REMAINS_ENDPOINT = "/v1/api/openplatform/coding_plan/remains"
# The API does not expose a plan-name field. model_name in the response is the
# quota bucket (e.g. "general", "video"), not the subscription plan.
PLAN_LABEL = "Token Plan"

STANDARD_MINIMAX_MODELS = [
    {"id": "MiniMax-M3", "display_name": "MiniMax-M3 (Flagship)"},
    {"id": "MiniMax-M2.7", "display_name": "MiniMax-M2.7"},
    {"id": "MiniMax-M2.7-highspeed", "display_name": "MiniMax-M2.7 HighSpeed"},
    {"id": "MiniMax-M2.5", "display_name": "MiniMax-M2.5"},
    {"id": "MiniMax-M2.5-highspeed", "display_name": "MiniMax-M2.5 HighSpeed"},
]


class APIError(Exception):
    pass


class APIAuthError(APIError):
    pass


class APIClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def _req(self, path, params=None):
        url = f"{API_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept-Language": "en-US,en",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                body = json.loads(r.read().decode())
                # MiniMax error codes are usually inside the response body too
                if isinstance(body, dict) and "base_resp" in body:
                    resp = body["base_resp"]
                    status_code = resp.get("status_code", 0)
                    status_msg = resp.get("status_msg", "")
                    if status_code != 0:
                        if status_code in (1004, 1011, 1024):
                            raise APIAuthError(
                                f"Auth error ({status_code}): {status_msg}"
                            )
                        raise APIError(f"MiniMax Error {status_code}: {status_msg}")
                return body
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise APIAuthError("Invalid API key or unauthorized access") from e
            raise APIError(f"API returned HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise APIError(f"Network error: {e.reason}") from e
        except TimeoutError as e:
            raise APIError("Network timeout contacting MiniMax API") from e
        except json.JSONDecodeError as e:
            raise APIError("Invalid response from API") from e

    def _try_models(self):
        try:
            data = self._req("/v1/models")
            raw_list = data.get("data") if isinstance(data, dict) else data
            if isinstance(raw_list, list) and len(raw_list) > 0:
                res = []
                for m in raw_list:
                    if isinstance(m, dict) and m.get("id"):
                        m_id = str(m["id"])
                        res.append(
                            {
                                "id": m_id,
                                "display_name": m_id,
                            }
                        )
                if res:
                    return res
        except Exception:
            pass
        return STANDARD_MINIMAX_MODELS

    @staticmethod
    def _rem_pct_from_model(m, kind):
        """Remaining percent for 'interval' or 'weekly'. Prefers the server-side
        `*_remaining_percent` field; falls back to count math; returns None if
        neither is available."""
        pct_key = f"current_{kind}_remaining_percent"
        if m.get(pct_key) is not None:
            return int(m[pct_key])
        total = m.get(f"current_{kind}_total_count", 0)
        used = m.get(f"current_{kind}_usage_count", 0)
        if total > 0:
            return int(max(0, total - used) / total * 100)
        return None

    @staticmethod
    def _is_enabled(m):
        """Best-effort: model is enabled on this plan if `*_status == 1`. If the
        status field is absent (older API), assume enabled so the app still
        renders something useful."""
        for key in ("current_interval_status", "current_weekly_status"):
            v = m.get(key)
            if v is not None:
                return v == 1
        return True

    @staticmethod
    def _epoch_ms_to_dt(val):
        return datetime.fromtimestamp(val / 1000) if val else None

    def _normalize(self, m):
        i_rem = self._rem_pct_from_model(m, "interval")
        w_rem = self._rem_pct_from_model(m, "weekly")
        interval_total = m.get("current_interval_total_count", 0)
        weekly_total = m.get("current_weekly_total_count", 0)
        interval_used = m.get("current_interval_usage_count", 0)
        weekly_used = m.get("current_weekly_usage_count", 0)

        return {
            "name": m.get("model_name", ""),
            "enabled": self._is_enabled(m),
            "interval_status": m.get("current_interval_status"),
            "weekly_status": m.get("current_weekly_status"),
            # Percent fields (None when the API doesn't expose them)
            "interval_rem_pct": i_rem,
            "weekly_rem_pct": w_rem,
            "interval_pct": (100 - i_rem) if i_rem is not None else None,
            "weekly_pct": (100 - w_rem) if w_rem is not None else None,
            # Raw counts (0 when not exposed; treat total=0 as "count unknown")
            "interval_used": interval_used,
            "interval_total": interval_total,
            "interval_remains": (
                max(0, interval_total - interval_used) if interval_total > 0 else None
            ),
            "weekly_used": weekly_used,
            "weekly_total": weekly_total,
            "weekly_remains": (
                max(0, weekly_total - weekly_used) if weekly_total > 0 else None
            ),
            "weekly_tracked": weekly_total > 0 or w_rem is not None,
            # Reset times in epoch ms (None when missing)
            "interval_reset_ms": (
                int(time.time() * 1000 + m["remains_time"])
                if m.get("remains_time")
                else None
            ),
            "weekly_reset_ms": (
                int(time.time() * 1000 + m["weekly_remains_time"])
                if m.get("weekly_remains_time")
                else None
            ),
            # Window boundaries
            "interval_start": self._epoch_ms_to_dt(m.get("start_time")),
            "interval_end": self._epoch_ms_to_dt(m.get("end_time")),
            "weekly_start": self._epoch_ms_to_dt(m.get("weekly_start_time")),
            "weekly_end": self._epoch_ms_to_dt(m.get("weekly_end_time")),
        }

    def fetch_all(self):
        r = self._req(REMAINS_ENDPOINT)
        models_list = r.get("model_remains", [])
        if not models_list:
            raise APIError("No model remains data found in API response")

        # Primary model: prefer enabled "general" bucket, then any enabled
        # model, then the first one.
        primary = None
        for m in models_list:
            if self._is_enabled(m) and m.get("model_name") == "general":
                primary = m
                break
        if primary is None:
            for m in models_list:
                if self._is_enabled(m):
                    primary = m
                    break
        if primary is None:
            primary = models_list[0]

        primary_data = self._normalize(primary)

        # Detail window: every bucket that exposes any percent field.
        all_models = [
            self._normalize(m)
            for m in models_list
            if self._rem_pct_from_model(m, "interval") is not None
            or self._rem_pct_from_model(m, "weekly") is not None
        ]

        supported_models = self._try_models()

        return {
            "plan_label": PLAN_LABEL,
            "model_name": primary_data["name"],
            "interval_pct": primary_data["interval_pct"],
            "interval_rem_pct": primary_data["interval_rem_pct"],
            "weekly_pct": primary_data["weekly_pct"],
            "weekly_rem_pct": primary_data["weekly_rem_pct"],
            "interval_used": primary_data["interval_used"],
            "interval_total": primary_data["interval_total"],
            "interval_remains": primary_data["interval_remains"],
            "weekly_used": primary_data["weekly_used"],
            "weekly_total": primary_data["weekly_total"],
            "weekly_remains": primary_data["weekly_remains"],
            "weekly_tracked": primary_data["weekly_tracked"],
            "interval_reset_ms": primary_data["interval_reset_ms"],
            "weekly_reset_ms": primary_data["weekly_reset_ms"],
            "interval_start": primary_data["interval_start"],
            "interval_end": primary_data["interval_end"],
            "weekly_start": primary_data["weekly_start"],
            "weekly_end": primary_data["weekly_end"],
            "all_models": all_models,
            "supported_models": supported_models,
            "ts": datetime.now(),
        }
