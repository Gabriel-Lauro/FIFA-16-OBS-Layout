import json
import os
import threading
from socketserver import ThreadingMixIn
from http.server import BaseHTTPRequestHandler, HTTPServer

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
PORT = 8000

_estado = None

# lista de eventos — cada cliente SSE recebe um threading.Event
# quando há dado novo, todos são notificados
_lock_subs = threading.Lock()
_subs_grupos: list[threading.Event] = []
_subs_aovivo: list[threading.Event] = []

# último payload de cada stream (para entregar imediatamente ao conectar)
_last_grupos: str = "{}"
_last_aovivo: str = "{}"


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Uma thread por conexão — SSE não bloqueia mais nada."""
    daemon_threads = True


def iniciar_servidor(estado):
    global _estado, _last_grupos, _last_aovivo
    _estado = estado
    _last_grupos = json.dumps(estado.snapshot_grupos())
    _last_aovivo = json.dumps(estado.snapshot_aovivo())
    estado.on_placar(_on_placar_changed)
    t = threading.Thread(target=_rodar, daemon=True)
    t.start()


def _rodar():
    server = ThreadingHTTPServer(("", PORT), Handler)
    server.serve_forever()


def _on_placar_changed(*_):
    broadcast_aovivo()
    broadcast_grupos()


def broadcast_aovivo():
    global _last_aovivo
    _last_aovivo = json.dumps(_estado.snapshot_aovivo())
    _notify(_subs_aovivo)


def broadcast_grupos():
    global _last_grupos
    _last_grupos = json.dumps(_estado.snapshot_grupos())
    _notify(_subs_grupos)


def _notify(subs: list):
    with _lock_subs:
        for ev in subs:
            ev.set()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/grupos"):
            self._serve_file("grupos.html")
        elif path == "/aovivo":
            self._serve_file("aovivo.html")
        elif path == "/stream/grupos":
            self._sse_stream(_subs_grupos, lambda: _last_grupos)
        elif path == "/stream/aovivo":
            self._sse_stream(_subs_aovivo, lambda: _last_aovivo)
        elif path == "/estado/grupos":
            self._json(_last_grupos)
        elif path == "/estado/aovivo":
            self._json(_last_aovivo)
        elif path.startswith("/css/") or path.startswith("/js/") or path.startswith("/img/"):
            self._serve_file(path.lstrip("/"))
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, name: str):
        full = os.path.join(STATIC_DIR, name)
        if not os.path.exists(full):
            self.send_response(404)
            self.end_headers()
            return
        ext = name.rsplit(".", 1)[-1]
        content_types = {
            "html": "text/html; charset=utf-8",
            "css":  "text/css; charset=utf-8",
            "js":   "application/javascript; charset=utf-8",
        }
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_types.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: str):
        body = payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse_stream(self, subs: list, get_payload):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        ev = threading.Event()
        with _lock_subs:
            subs.append(ev)

        try:
            # entrega snapshot imediato
            self._sse_write(get_payload())

            while True:
                triggered = ev.wait(timeout=20)
                if triggered:
                    ev.clear()
                    self._sse_write(get_payload())
                else:
                    # heartbeat para manter conexão viva
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except Exception:
            pass
        finally:
            with _lock_subs:
                if ev in subs:
                    subs.remove(ev)

    def _sse_write(self, payload: str):
        self.wfile.write(f"data: {payload}\n\n".encode())
        self.wfile.flush()
