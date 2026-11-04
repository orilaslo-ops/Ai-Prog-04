#!/usr/bin/env python3
"""dashboard.py: live agent-traffic dashboard as a WhatsApp-style group chat (build 4, from SPEC.md).

A pass-through reverse proxy that sits in front of proxy.py (or the API),
forwards every request unchanged, streams every reply back byte for byte, and
records a copy of each exchange for a live browser dashboard.

    python3 proxy.py --port 8041                                   # terminal 1
    python3 builds/b4/dashboard.py --port 8042 --upstream http://localhost:8041   # terminal 2
    ANTHROPIC_BASE_URL=http://localhost:8042 claude                # terminal 3
    # open http://localhost:8042/dashboard

Python 3.8+ standard library only.
"""

from __future__ import annotations

import argparse
import http.client
import itertools
import json
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

# Hop-by-hop headers, never forwarded (same list as proxy.py).
SKIP = {
    "host", "connection", "keep-alive", "transfer-encoding", "te", "trailers",
    "upgrade", "proxy-authorization", "proxy-authenticate", "accept-encoding",
    "content-length",
}
SECRET_HEADERS = {"authorization", "x-api-key", "cookie", "proxy-authorization"}

UPSTREAM = "http://localhost:8041"
HERE = os.path.dirname(os.path.abspath(__file__))

# USD per million tokens: (input, output, cache read, cache write 5m).
# Matched by longest prefix of the model name. Unknown model -> cost "n/a".
PRICES = {
    "claude-fable-5":    (10.00, 50.00, 0.25, 12.50),
    "claude-mythos-5":   (10.00, 50.00, 0.25, 12.50),
    "claude-opus-5-5":   (4.00, 20.00, 0.20, 5.00),
    "claude-opus-5":     (5.00, 25.00, 0.50, 6.25),
    "claude-opus-4-8":   (5.00, 25.00, 0.50, 6.25),
    "claude-opus-4-7":   (5.00, 25.00, 0.50, 6.25),
    "claude-opus-4-6":   (5.00, 25.00, 0.50, 6.25),
    "claude-opus-4-5":   (5.00, 25.00, 0.50, 6.25),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-sonnet-5":   (2.00, 10.00, 0.20, 2.50),
    "claude-sonnet-4":   (3.00, 15.00, 0.30, 3.75),
    "claude-haiku-5-5":  (0.10, 0.50, 0.01, 0.125),
    "claude-haiku-4-5":  (1.00, 5.00, 0.10, 1.25),
    "claude-3-5-haiku":  (0.80, 4.00, 0.08, 1.00),
}


# Context window in tokens, matched by longest prefix like PRICES (section 12).
# Unknown model -> None (the page shows "?"). A request that carries the
# "context-1m" beta header gets 1 000 000.
CONTEXT_WINDOWS = {
    "claude-fable-5": 200_000, "claude-mythos-5": 200_000,
    "claude-opus-5": 200_000, "claude-opus-4": 200_000,
    "claude-sonnet-5": 200_000, "claude-sonnet-4": 200_000,
    "claude-haiku-5": 200_000, "claude-haiku-4": 200_000,
    "claude-3-5-haiku": 200_000, "claude-3": 200_000,
}


def context_window_for(model: str, beta: str):
    best = None
    for prefix, n in CONTEXT_WINDOWS.items():
        if model and model.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, n)
    if not best:
        return None
    return 1_000_000 if "context-1m" in (beta or "") else best[1]


def price_for(model: str):
    best = None
    for prefix, p in PRICES.items():
        if model and model.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, p)
    return best[1] if best else None


def cost_of(model: str, usage: dict):
    p = price_for(model or "")
    if not p or not usage:
        return None
    return (
        (usage.get("input_tokens") or 0) * p[0]
        + (usage.get("output_tokens") or 0) * p[1]
        + (usage.get("cache_read_input_tokens") or 0) * p[2]
        + (usage.get("cache_creation_input_tokens") or 0) * p[3]
    ) / 1_000_000


def mask(name: str, value: str) -> str:
    if name.lower() in SECRET_HEADERS:
        return value[:12] + "..."
    return value


# ---------------------------------------------------------------- event bus
class Bus:
    """Fan-out of dashboard events to every open SSE connection (no history)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.clients: list = []

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self.lock:
            self.clients.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def publish(self, event: dict) -> None:
        data = json.dumps(event, ensure_ascii=False)
        with self.lock:
            for q in self.clients:
                q.put(data)


BUS = Bus()
COUNTER = itertools.count(1)


# ------------------------------------------------------ reply reassembly
class ReplyParser:
    """Rebuilds a complete Messages API reply from the raw bytes of the body.

    Handles both a streamed reply (SSE events) and a plain JSON reply.
    """

    def __init__(self, content_type: str) -> None:
        self.is_sse = "text/event-stream" in (content_type or "")
        self.buf = b""
        self.raw = bytearray()
        self.blocks: dict = {}       # index -> block
        self.partial_json: dict = {}  # index -> accumulated input_json string
        self.usage: dict = {}
        self.message: dict = {}
        self.stop_reason = None
        self.error = None

    def feed(self, chunk: bytes) -> None:
        if not self.is_sse:
            self.raw.extend(chunk)
            return
        self.buf += chunk
        while True:
            # Events are separated by a blank line (\n\n or \r\n\r\n).
            idx = self.buf.find(b"\n\n")
            idx_r = self.buf.find(b"\r\n\r\n")
            if idx_r != -1 and (idx == -1 or idx_r < idx):
                raw_event, self.buf = self.buf[:idx_r], self.buf[idx_r + 4:]
            elif idx != -1:
                raw_event, self.buf = self.buf[:idx], self.buf[idx + 2:]
            else:
                break
            self._event(raw_event.decode("utf-8", "replace"))

    def _event(self, text: str) -> None:
        data_lines = []
        for line in text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            return
        try:
            ev = json.loads("\n".join(data_lines))
        except ValueError:
            return
        t = ev.get("type")
        if t == "message_start":
            self.message = ev.get("message") or {}
            self.usage.update(self.message.get("usage") or {})
        elif t == "content_block_start":
            block = dict(ev.get("content_block") or {})
            if block.get("type") in ("tool_use", "server_tool_use"):
                block["input"] = {}
                self.partial_json[ev["index"]] = ""
            self.blocks[ev.get("index", len(self.blocks))] = block
        elif t == "content_block_delta":
            i = ev.get("index")
            d = ev.get("delta") or {}
            b = self.blocks.setdefault(i, {"type": "text", "text": ""})
            dt = d.get("type")
            if dt == "text_delta":
                b["text"] = b.get("text", "") + d.get("text", "")
            elif dt == "input_json_delta":
                self.partial_json[i] = self.partial_json.get(i, "") + d.get("partial_json", "")
            elif dt == "thinking_delta":
                b["thinking"] = b.get("thinking", "") + d.get("thinking", "")
            elif dt == "signature_delta":
                b["signature"] = "(signature)"
        elif t == "content_block_stop":
            i = ev.get("index")
            if i in self.partial_json:
                s = self.partial_json.pop(i)
                try:
                    self.blocks[i]["input"] = json.loads(s) if s.strip() else {}
                except ValueError:
                    self.blocks[i]["input"] = {"_unparsed": s}
        elif t == "message_delta":
            d = ev.get("delta") or {}
            if d.get("stop_reason"):
                self.stop_reason = d["stop_reason"]
            for k, v in (ev.get("usage") or {}).items():
                if v is not None:
                    self.usage[k] = v
        elif t == "error":
            self.error = ev.get("error") or ev

    def result(self) -> dict:
        if self.is_sse:
            # Flush any unfinished partial JSON (stream cut short).
            for i, s in self.partial_json.items():
                self.blocks[i]["input"] = {"_unparsed": s}
            content = [self.blocks[i] for i in sorted(self.blocks)]
            return {
                "content": content, "usage": self.usage, "stop_reason": self.stop_reason,
                "model": self.message.get("model"), "error": self.error, "streamed": True,
            }
        text = bytes(self.raw).decode("utf-8", "replace")
        try:
            obj = json.loads(text) if text.strip() else None
        except ValueError:
            obj = None
        if isinstance(obj, dict) and isinstance(obj.get("content"), list):
            return {
                "content": obj["content"], "usage": obj.get("usage") or {},
                "stop_reason": obj.get("stop_reason"), "model": obj.get("model"),
                "error": None, "streamed": False,
            }
        if isinstance(obj, dict) and obj.get("type") == "error":
            return {"content": [], "usage": {}, "error": obj.get("error") or obj, "streamed": False}
        # Something else (count_tokens result, models list, plain text...).
        return {"content": [], "usage": {}, "error": None, "streamed": False,
                "other": obj if obj is not None else text[:20000]}


# ---------------------------------------------------------------- handler
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in ("/dashboard", "/dashboard/"):
            return self.serve_page()
        if path == "/dashboard/events":
            return self.serve_events()
        self.relay()

    def do_POST(self) -> None:
        self.relay()

    def do_HEAD(self) -> None:
        self.relay()

    def do_PUT(self) -> None:
        self.relay()

    def do_DELETE(self) -> None:
        self.relay()

    def do_PATCH(self) -> None:
        self.relay()

    def do_OPTIONS(self) -> None:
        self.relay()

    # ---- dashboard page + SSE
    def serve_page(self) -> None:
        with open(os.path.join(HERE, "dashboard.html"), "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve_events(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        q = BUS.subscribe()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    data = q.get(timeout=15)
                    self.wfile.write(b"data: " + data.encode("utf-8") + b"\n\n")
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            BUS.unsubscribe(q)

    # ---- pass-through proxy
    def relay(self) -> None:
        ex_id = next(COUNTER)
        started = time.time()
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else b""

        try:
            parsed = json.loads(body) if body else None
        except ValueError:
            parsed = None
        req = parsed if isinstance(parsed, dict) else {}
        BUS.publish({
            "type": "request", "id": ex_id,
            "data": {
                "method": self.command, "path": self.path,
                "headers": {k: mask(k, v) for k, v in self.headers.items()},
                "model": req.get("model"), "system": req.get("system"),
                "tools": req.get("tools"), "messages": req.get("messages"),
                "params": {k: v for k, v in req.items() if k not in ("system", "tools", "messages")},
                "raw_body": None if parsed is not None or not body else body[:20000].decode("utf-8", "replace"),
                "started_at": started * 1000,
            },
        })

        target = urlsplit(UPSTREAM)
        conn_cls = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
        upstream = conn_cls(target.netloc, timeout=10)
        try:
            upstream.connect()
            upstream.sock.settimeout(600)
            headers = {k: v for k, v in self.headers.items() if k.lower() not in SKIP}
            upstream.request(self.command, target.path.rstrip("/") + self.path, body=body or None, headers=headers)
            reply = upstream.getresponse()
        except OSError as e:
            msg = f"dashboard: cannot reach {UPSTREAM}: {e}"
            self.send_error(502, msg)
            self.close_connection = True
            self.publish_reply(ex_id, req, started, None, 502, {"content": [], "usage": {},
                               "error": {"type": "proxy_error", "message": msg}})
            return

        self.send_response(reply.status, reply.reason)
        for name, value in reply.getheaders():
            if name.lower() not in SKIP and name.lower() != "content-encoding":
                self.send_header(name, value)
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        parser = ReplyParser(reply.getheader("content-type", ""))
        ttfb = None
        first_byte = False
        try:
            if self.command != "HEAD":
                while True:
                    chunk = reply.read1(65536)
                    if not chunk:
                        break
                    if ttfb is None:
                        ttfb = (time.time() - started) * 1000
                        first_byte = True
                    # The agent comes first: write before parsing.
                    self.wfile.write(chunk)
                    self.wfile.flush()
                    if first_byte:  # for the ✓✓ ticks (section 12), after the agent got the byte
                        first_byte = False
                        BUS.publish({"type": "first_byte", "id": ex_id, "data": {"ttfb_ms": round(ttfb)}})
                    try:
                        parser.feed(chunk)
                    except Exception:  # never let the dashboard break the agent
                        pass
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            parser.error = {"type": "connection", "message": str(e)}
        finally:
            upstream.close()
        try:
            result = parser.result()
        except Exception as e:  # pragma: no cover
            result = {"content": [], "usage": {}, "error": {"type": "parse", "message": str(e)}}
        self.publish_reply(ex_id, req, started, ttfb, reply.status, result)

    def publish_reply(self, ex_id, req, started, ttfb, status, result) -> None:
        model = result.get("model") or req.get("model")
        result.update({
            "status": status,
            "ttfb_ms": round(ttfb) if ttfb is not None else None,
            "total_ms": round((time.time() - started) * 1000),
            "cost": cost_of(model, result.get("usage") or {}),
            "context_window": context_window_for(model, self.headers.get("anthropic-beta", "")),
        })
        BUS.publish({"type": "reply", "id": ex_id, "data": result})


def main() -> None:
    global UPSTREAM
    ap = argparse.ArgumentParser(description="Live dashboard for an agent's API traffic.")
    ap.add_argument("--port", type=int, default=8042)
    ap.add_argument("--upstream", default=UPSTREAM, help="where to forward (default: proxy.py on 8041)")
    args = ap.parse_args()
    UPSTREAM = args.upstream.rstrip("/")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    print(f"dashboard proxy on http://localhost:{args.port}  ->  {UPSTREAM}")
    print(f"open the dashboard:  http://localhost:{args.port}/dashboard")
    print(f"run the agent with:  ANTHROPIC_BASE_URL=http://localhost:{args.port} claude")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
