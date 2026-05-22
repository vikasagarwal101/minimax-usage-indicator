import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

API_BASE = "https://api.minimax.io"


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
                            raise APIAuthError(f"Auth error ({status_code}): {status_msg}")
                        raise APIError(f"MiniMax Error {status_code}: {status_msg}")
                return body
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise APIAuthError("Invalid API key or unauthorized access") from e
            raise APIError(f"API returned HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise APIError(f"Network error: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise APIError("Invalid response from API") from e

    def fetch_all(self):
        try:
            r = self._req("/v1/token_plan/remains")
        except APIAuthError:
            raise
        except APIError:
            raise

        models_list = r.get("model_remains", [])
        if not models_list:
            raise APIError("No model remains data found in API response")

        # Select primary model: prefer MiniMax-M* or coding-plan, fallback to first with interval limit
        primary = None
        for m in models_list:
            name = m.get("model_name", "")
            if name.startswith("MiniMax-M") or "coding-plan" in name:
                primary = m
                break
        if not primary:
            for m in models_list:
                if m.get("current_interval_total_count", 0) > 0:
                    primary = m
                    break
        if not primary:
            primary = models_list[0]

        # Extract primary metrics
        model_name = primary.get("model_name", "MiniMax-M*")
        
        # Interval
        interval_used = primary.get("current_interval_usage_count", 0)
        interval_total = primary.get("current_interval_total_count", 0)
        interval_remains = max(0, interval_total - interval_used)
        interval_rem_pct = int((interval_remains / interval_total) * 100) if interval_total > 0 else 100
        
        # remains_time is returned in milliseconds
        remains_time = primary.get("remains_time", 0)
        interval_reset_ms = int(time.time() * 1000 + remains_time) if remains_time else None

        # Weekly
        weekly_used = primary.get("current_weekly_usage_count", 0)
        weekly_total = primary.get("current_weekly_total_count", 0)
        weekly_remains = max(0, weekly_total - weekly_used)
        weekly_rem_pct = int((weekly_remains / weekly_total) * 100) if weekly_total > 0 else 100
        
        weekly_remains_time = primary.get("weekly_remains_time", 0)
        weekly_reset_ms = int(time.time() * 1000 + weekly_remains_time) if weekly_remains_time else None

        # Parse epochs (which are in milliseconds from MiniMax API)
        def parse_epoch(val):
            return datetime.fromtimestamp(val / 1000) if val else None

        interval_start = parse_epoch(primary.get("start_time"))
        interval_end = parse_epoch(primary.get("end_time"))
        weekly_start = parse_epoch(primary.get("weekly_start_time"))
        weekly_end = parse_epoch(primary.get("weekly_end_time"))

        # Build list of all active models to show in expanded panel
        all_models = []
        for m in models_list:
            m_total = m.get("current_interval_total_count", 0)
            m_wk_total = m.get("current_weekly_total_count", 0)
            # Only include models that have actual limits configured
            if m_total > 0 or m_wk_total > 0:
                m_used = m.get("current_interval_usage_count", 0)
                m_rem = max(0, m_total - m_used)
                m_rem_pct = int((m_rem / m_total) * 100) if m_total > 0 else 100
                m_used_pct = 100 - m_rem_pct
                
                m_wk_used = m.get("current_weekly_usage_count", 0)
                m_wk_rem = max(0, m_wk_total - m_wk_used)
                m_wk_rem_pct = int((m_wk_rem / m_wk_total) * 100) if m_wk_total > 0 else 100
                m_wk_used_pct = 100 - m_wk_rem_pct
                
                all_models.append({
                    "name": m.get("model_name", ""),
                    "interval_remains": m_rem,
                    "interval_total": m_total,
                    "interval_rem_pct": m_rem_pct,
                    "interval_used_pct": m_used_pct,
                    "weekly_remains": m_wk_rem,
                    "weekly_total": m_wk_total,
                    "weekly_rem_pct": m_wk_rem_pct,
                    "weekly_used_pct": m_wk_used_pct,
                })

        return {
            "model_name": model_name,
            "interval_remains": interval_remains,
            "interval_total": interval_total,
            "interval_used": interval_used,
            "interval_pct": 100 - interval_rem_pct,  # Usage percentage
            "interval_rem_pct": interval_rem_pct,     # Remaining percentage
            "interval_reset_ms": interval_reset_ms,
            "interval_start": interval_start,
            "interval_end": interval_end,
            "weekly_remains": weekly_remains,
            "weekly_total": weekly_total,
            "weekly_used": weekly_used,
            "weekly_pct": 100 - weekly_rem_pct,       # Usage percentage
            "weekly_rem_pct": weekly_rem_pct,         # Remaining percentage
            "weekly_reset_ms": weekly_reset_ms,
            "weekly_start": weekly_start,
            "weekly_end": weekly_end,
            "all_models": all_models,
            "ts": datetime.now(),
        }


