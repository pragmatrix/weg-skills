#!/usr/bin/env python3
"""Nimmt Dateien aus dem ETG24-Portal entgegen und speichert sie in einen Ordner.

Aufruf:
    python3 -I etg24_recv.py ZIELORDNER

Hintergrund: Der Download-Knopf im Portal erzeugt die Datei als Blob in der Seite. Ein Klick, den ein Agent per
JavaScript auslöst, kommt aber nicht in `~/Downloads` an. Deshalb schickt die Seite den Blob per POST an diesen
Empfänger. Ablauf und JavaScript stehen im Skill `etg24-portal`.

Unter `/etg24.js` liefert er außerdem den Helfer aus dem Skill aus, den die Seite damit selbst nachlädt.

Der Empfänger lauscht nur auf 127.0.0.1:8765 und nimmt nur Anfragen der Seite https://app.etg24.de an. Den
Dateinamen liefert der Kopf `X-Name`. Davon zählt nur der letzte Pfadteil. Eine vorhandene Datei wird nie
überschrieben, der neue Name bekommt dann einen Zähler. Beenden mit Ctrl-C oder `pkill -f etg24_recv.py`.
"""
from pathlib import Path
import errno
import http.server
import subprocess
import sys
import urllib.parse

ORIGIN = "https://app.etg24.de"
PORT = 8765
HELPER = Path(__file__).resolve().parent / "etg24.js"


def free_name(out, name):
    """Gibt einen Pfad in `out` zurück, der noch nicht existiert."""
    path = out / name
    n = 2
    while path.exists():
        path = out / f"{Path(name).stem} ({n}){Path(name).suffix}"
        n += 1
    return path


def handler(out):
    class Handler(http.server.BaseHTTPRequestHandler):
        def cors(self):
            self.send_header("Access-Control-Allow-Origin", ORIGIN)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "X-Name, Content-Type")
            # Chrome fragt vor Anfragen einer öffentlichen Seite an localhost, ob das lokale Netz erlaubt ist.
            self.send_header("Access-Control-Allow-Private-Network", "true")

        def do_OPTIONS(self):
            self.send_response(204)
            self.cors()
            self.end_headers()

        def do_GET(self):
            # Liefert nur den Helfer aus dem Skill aus, damit der Agent ihn nicht als Text einfügen muss.
            if self.path != "/etg24.js":
                self.send_response(404)
                self.end_headers()
                return
            body = HELPER.read_bytes()
            self.send_response(200)
            self.cors()
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.headers.get("Origin") != ORIGIN:
                self.send_response(403)
                self.end_headers()
                return
            name = Path(urllib.parse.unquote(self.headers.get("X-Name", "ohne Namen.pdf"))).name
            data = self.rfile.read(int(self.headers["Content-Length"]))
            path = free_name(out, name)
            path.write_bytes(data)
            print(f"gespeichert: {path.name} ({len(data)} Bytes)", flush=True)
            self.send_response(200)
            self.cors()
            self.end_headers()
            self.wfile.write(path.name.encode())

    return Handler


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    try:
        server = http.server.HTTPServer(("127.0.0.1", PORT), handler(out))
    except OSError as e:
        if e.errno != errno.EADDRINUSE:
            raise
        sys.exit(f"etg24_recv: Port {PORT} ist belegt, vermutlich durch einen Empfänger einer anderen Sitzung:\n"
                 f"{running()}\nBeenden mit `pkill -f etg24_recv.py`, wenn er nicht mehr gebraucht wird.")
    print(f"etg24_recv: http://127.0.0.1:{PORT}/ → {out}", flush=True)
    server.serve_forever()


def running():
    """PID, Startzeit und Aufruf des Prozesses, der den Port belegt, mit seinem Zielordner."""
    pids = subprocess.run(["lsof", "-t", f"-iTCP:{PORT}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
    if not pids:
        return "(Prozess nicht gefunden)"
    return subprocess.run(["ps", "-o", "pid=,lstart=,command=", "-p", ",".join(pids)],
                          capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    main()
