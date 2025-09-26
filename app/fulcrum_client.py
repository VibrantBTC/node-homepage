import json
import socket
import ssl

def electrum_request(host: str, port: int, method: str,
                     params=None, use_ssl=True, timeout=5):
    params = params or []
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    payload = (json.dumps(req) + "\n").encode()

    s = socket.create_connection((host, port), timeout=timeout)
    if use_ssl:
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=host)

    s.sendall(payload)

    buff = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buff += chunk
        if b"\n" in buff:
            break
    s.close()

    text = buff.decode().strip()
    if not text:
        raise RuntimeError("Empty response from Fulcrum")
    resp = json.loads(text)
    if "error" in resp and resp["error"]:
        raise RuntimeError(str(resp["error"]))
    return resp.get("result")

def get_fulcrum_stats(host: str, port: int, use_ssl=True):
    version = electrum_request(host, port, "server.version", ["node-homepage", "1.5"],
                               use_ssl=use_ssl)
    headers = electrum_request(host, port, "blockchain.headers.subscribe",
                               [], use_ssl=use_ssl)
    height = headers.get("height", 0)
    return {
        "version": version[0] if isinstance(version, (list, tuple)) else str(version),
        "height": height,
    }
