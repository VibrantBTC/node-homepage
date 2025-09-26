from flask import Flask, jsonify, render_template, request, send_file
import io
import os
import re
from collections import deque
import requests
import qrcode
from qrcode.image.pil import PilImage
from config import load_config

app = Flask(__name__, static_folder="static", template_folder="templates")
CFG = load_config()

def rpc_call(method, params=None):
    params = params or []
    url = f"http://{CFG['bitcoin']['rpc_host']}:{CFG['bitcoin']['rpc_port']}"
    auth = (CFG['bitcoin']['rpc_user'], CFG['bitcoin']['rpc_pass'])
    payload = {"jsonrpc": "1.0", "id": "node-homepage", "method": method,
               "params": params}
    r = requests.post(url, json=payload, auth=auth, timeout=5)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data["result"]

def seconds_to_dhms(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{days}d {hours}h {minutes}m {secs}s"

@app.route("/")
def index():
    return render_template("index.html", cfg=CFG)

@app.route("/api/bitcoin")
def api_bitcoin():
    try:
        info = rpc_call("getblockchaininfo")
        mempool = rpc_call("getmempoolinfo")
        net = rpc_call("getnetworkinfo")
        uptime = rpc_call("uptime")

        headers = info.get("headers", 0) or 0
        blocks = info.get("blocks", 0) or 0
        sync_percent = round((blocks / headers) * 100, 2) if headers else 0.0

        return jsonify({
            "version": net.get("subversion", "").strip("/").replace("Satoshi:", ""),
            "blocks": blocks,
            "headers": headers,
            "sync_percent": sync_percent,
            "disk_size_gb": round(info.get("size_on_disk", 0) / 1e9, 2),
            "mempool_mb": round(mempool.get("usage", 0) / (1024 * 1024), 2),
            "connections": {
                "total": net.get("connections", 0),
                "inbound": net.get("connections_in", 0),
                "outbound": net.get("connections_out", 0),
            },
            "uptime": seconds_to_dhms(uptime),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- Fulcrum logs-only parsing with “up-to-date” height ----------

# Progress lines, e.g.:
# Processed height: 428000, 46.7%, 4.24 blocks/sec, 6293.2 txs/sec, 22361.2 addrs/sec
LOG_RE = re.compile(
    r"Processed height:\s*(\d+),\s*([0-9.]+)%,\s*([0-9.]+)\s*blocks/sec,\s*"
    r"([0-9.]+)\s*txs/sec,\s*([0-9.]+)\s*addrs/sec"
)

# Synced marker with explicit height, e.g.:
# Block height 840000, up-to-date
UPTODATE_RE = re.compile(r"Block height\s*(\d+),\s*up-to-date", re.IGNORECASE)

def read_tail_text(path: str, max_lines: int) -> str | None:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", errors="ignore") as f:
            dq = deque(f, maxlen=max_lines)
        return "".join(dq)
    except Exception:
        return None

def parse_fulcrum_tail(text: str):
    """
    Scan the tail text and return:
      - last_processed: dict with height, percent, speeds, index (or None)
      - last_uptodate: dict with height, index (or None)

    We consider 'synced' if 'Block height <N>, up-to-date' appears anywhere
    in the tail. When synced, we use that <N> as the displayed height.
    """
    lines = text.splitlines()
    last_processed = None
    last_uptodate = None

    for i, line in enumerate(lines):
        # Track the up-to-date line with height
        mu = UPTODATE_RE.search(line)
        if mu:
            try:
                uheight = int(mu.group(1))
            except Exception:
                uheight = None
            last_uptodate = {"index": i, "height": uheight}

        # Track last processed height line
        mp = LOG_RE.search(line)
        if mp:
            try:
                pheight = int(mp.group(1))
                percent = float(mp.group(2))
                bps = float(mp.group(3))
                tps = float(mp.group(4))
                aps = float(mp.group(5))
            except Exception:
                continue
            last_processed = {
                "index": i,
                "height": pheight,
                "percent": percent,
                "speeds": {
                    "blocks_per_sec": bps,
                    "txs_per_sec": tps,
                    "addrs_per_sec": aps,
                },
            }

    return last_processed, last_uptodate

@app.route("/api/fulcrum")
def api_fulcrum():
    # Check Bitcoin dependency so we can show "Bitcoin down" in the UI if needed
    bitcoin_up = True
    try:
        rpc_call("getblockchaininfo")
    except Exception:
        bitcoin_up = False

    # Version from env (logs don't include this)
    fl_version = CFG["fulcrum"].get("version") or None

    # If stats disabled, return minimal payload but still include version
    if not CFG["fulcrum"].get("stats_enabled", True):
        return jsonify({
            "source": "disabled",
            "bitcoin_up": bitcoin_up,
            "version": fl_version,
            "height": None,
            "sync_percent": 0.0,
            "status": "Hidden",
        })

    text = read_tail_text(CFG["fulcrum"]["tail_path"], CFG["fulcrum"]["tail_lines"])
    if not text:
        return jsonify({
            "source": "logs",
            "bitcoin_up": bitcoin_up,
            "version": fl_version,
            "height": None,
            "sync_percent": 0.0,
            "status": "Starting...",
        })

    last_processed, last_uptodate = parse_fulcrum_tail(text)

    # If up-to-date appears anywhere, consider synced and use its height
    if last_uptodate is not None:
        return jsonify({
            "source": "logs",
            "bitcoin_up": bitcoin_up,
            "version": fl_version,
            "height": last_uptodate.get("height"),
            "sync_percent": 100.0,
            "status": "Synced",
            "speeds": None,  # hide speeds when synced
        })

    # Otherwise, fall back to the last processed height (Indexing), if present
    if last_processed:
        percent = round(min(100.0, float(last_processed["percent"])), 2)
        return jsonify({
            "source": "logs",
            "bitcoin_up": bitcoin_up,
            "version": fl_version,
            "height": last_processed["height"],
            "sync_percent": percent,
            "status": "Indexing",
            "speeds": last_processed["speeds"],
        })

    # Neither processed nor up-to-date present
    return jsonify({
        "source": "logs",
        "bitcoin_up": bitcoin_up,
        "version": fl_version,
        "height": None,
        "sync_percent": 0.0,
        "status": "Starting...",
    })

def make_qr_png(text: str, box_size=8, border=2):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img: PilImage = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

@app.route("/qr")
def qr_generic():
    text = request.args.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    png = make_qr_png(text)
    return send_file(png, mimetype="image/png")

@app.route("/qr/dojo")
def qr_dojo():
    raw = CFG["dojo"].get("raw_final_min", "")
    if not raw:
        return jsonify({"error": "Dojo pairing JSON not configured"}), 400
    png = make_qr_png(raw)
    return send_file(png, mimetype="image/png")

if __name__ == "__main__":
    port = CFG["app_port"]
    app.run(host="0.0.0.0", port=port, debug=False)
