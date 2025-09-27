import os
import json

def getenv_bool(key, default="false"):
    val = os.getenv(key, default).strip().lower()
    return val in ("1", "true", "yes", "on")

def first_nonempty(*vals):
    for v in vals:
        if v and str(v).strip():
            return str(v).strip()
    return ""

def ensure_v2_suffix(url: str) -> str:
    """Ensure the URL ends with '/v2' exactly (no trailing slash beyond /v2)."""
    if not url:
        return ""
    u = url.strip().rstrip("/")
    if not u.endswith("/v2"):
        u = u + "/v2"
    return u

def ensure_http(url: str) -> str:
    """
    If url has no scheme, prefix with 'http://'.
    Used for onion addresses pasted without scheme.
    """
    if not url:
        return ""
    u = url.strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return "http://" + u

def canonical_dojo(version: str, apikey: str, pairing_url: str, explorer_url: str):
    return {
        "pairing": {
            "type": "dojo.api",
            "version": version or "",
            "apikey": apikey or "",
            "url": ensure_v2_suffix(pairing_url or ""),
        },
        "explorer": {
            "type": "explorer.btc_rpc_explorer",
            "url": explorer_url or "",
        },
    }

def load_config():
    mempool_clearnet = first_nonempty(
        os.getenv("MEMPOOL_CLEARNET", ""),
        os.getenv("MEMPOOL_LOCAL", "")
    )
    robosats_clearnet = first_nonempty(
        os.getenv("ROBOSATS_CLEARNET", ""),
        os.getenv("ROBOSATS_LOCAL", "")
    )

    cfg = {
        "app_title": os.getenv("APP_TITLE", "Bitcoin Node"),
        "app_port": int(os.getenv("APP_PORT", "8088")),

        "bitcoin": {
            "rpc_host": os.getenv("BITCOIN_RPC_HOST", "127.0.0.1"),
            "rpc_port": int(os.getenv("BITCOIN_RPC_PORT", "8332")),
            "rpc_user": os.getenv("BITCOIN_RPC_USER", ""),
            "rpc_pass": os.getenv("BITCOIN_RPC_PASS", ""),
            "p2p_onion": os.getenv("BITCOIN_P2P_ONION", ""),
            "p2p_port": int(os.getenv("BITCOIN_P2P_PORT", "8333")),
        },

        "fulcrum": {
            "backend_host": os.getenv("FULCRUM_BACKEND_HOST", "127.0.0.1"),
            "tcp_port": int(os.getenv("FULCRUM_TCP_PORT", "50001")),
            "ssl_port": int(os.getenv("FULCRUM_SSL_PORT", "50002")),
            "local_address": os.getenv("FULCRUM_LOCAL_ADDRESS", "hostname.local"),
            "onion_tcp": os.getenv("FULCRUM_ONION_TCP", ""),
            "onion_ssl": os.getenv("FULCRUM_ONION_SSL", ""),
            "use_ssl": getenv_bool("FULCRUM_USE_SSL", "false"),
            "stats_enabled": getenv_bool("FULCRUM_STATS", "true"),
            "tail_path": os.getenv("FULCRUM_TAIL_PATH", "/app/fulcrum_tail.log").strip(),
            "tail_lines": int(os.getenv("FULCRUM_TAIL_LINES", "100")),
            "version": os.getenv("FULCRUM_VERSION", "").strip(),
        },

        "dojo": {
            "raw_json": os.getenv("DOJO_RAW_JSON", "").strip(),
            "apikey": os.getenv("DOJO_APIKEY", "").strip(),
            "url": os.getenv("DOJO_URL", "").strip(),
            "version": os.getenv("DOJO_VERSION", "1.27.0").strip(),
            "explorer_url": os.getenv("EXPLORER_URL", "").strip(),
            # Normalize maintenance URL to ensure http:// if missing
            "maintenance_url": ensure_http(os.getenv("DOJO_MAINTENANCE_URL", "").strip()),
        },

        "mempool": {
            "clearnet": mempool_clearnet,
            "onion": os.getenv("MEMPOOL_ONION", "").strip(),
        },

        "robosats": {
            "clearnet": robosats_clearnet,
            "onion": os.getenv("ROBOSATS_ONION", "").strip(),
        },

        "monero": {
            "onion": os.getenv("MONERO_ONION", "").strip(),
            "rpc_port": int(os.getenv("MONERO_RPC_PORT", "18089")),
        },
    }

    # Build/normalize Dojo JSON
    raw = cfg["dojo"]["raw_json"]
    if raw:
        try:
            src = json.loads(raw)
        except Exception:
            src = {}
        pairing = src.get("pairing", {}) if isinstance(src.get("pairing"), dict) else {}
        explorer = src.get("explorer", {}) if isinstance(src.get("explorer"), dict) else {}
        version = cfg["dojo"]["version"] or pairing.get("version", "1.27.0")
        apikey = cfg["dojo"]["apikey"] or pairing.get("apikey", "")
        pairing_url = cfg["dojo"]["url"] or pairing.get("url", "")
        explorer_url = cfg["dojo"]["explorer_url"] or explorer.get("url", "")
        data = canonical_dojo(version, apikey, pairing_url, explorer_url)
    else:
        data = canonical_dojo(
            cfg["dojo"]["version"],
            cfg["dojo"]["apikey"],
            cfg["dojo"]["url"],
            cfg["dojo"]["explorer_url"],
        )

    # Override explorer.url to mempool onion if provided
    mem_onion = cfg["mempool"]["onion"]
    if mem_onion:
        data["explorer"]["url"] = f"http://{mem_onion}"

    try:
        raw_min = json.dumps(data, separators=(",", ":"))
        raw_pretty = json.dumps(data, indent=4)
        valid = True
    except Exception:
        raw_min = ""
        raw_pretty = ""
        valid = False

    cfg["dojo"]["json"] = data
    cfg["dojo"]["raw_final_min"] = raw_min
    cfg["dojo"]["raw_final_pretty"] = raw_pretty
    cfg["dojo"]["valid"] = valid

    return cfg
