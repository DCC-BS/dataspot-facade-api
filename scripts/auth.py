import json
import os
import platform
import subprocess
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
AUTH_URL = f"{API_BASE}/v1/auth"
DOCS_SPEC_URL = f"{API_BASE}/openapi.json"
SWAGGER_UI_VERSION = "5.18.2"
DOCS_SERVER_PORT = 8090


def get_jwt_token(access_key: str) -> str:
    data = json.dumps({"access_key": access_key}).encode("utf-8")
    req = Request(
        AUTH_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["access_token"]


def copy_to_clipboard(text: str) -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif system == "Linux":
            if os.environ.get("WAYLAND_DISPLAY"):
                subprocess.run(["wl-copy"], input=text.encode(), check=True)
            else:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(),
                    check=True,
                )
        elif system == "Windows":
            subprocess.run(["clip.exe"], input=text.encode(), check=True)
        else:
            _tkinter_clipboard(text)
    except FileNotFoundError:
        _tkinter_clipboard(text)


def _tkinter_clipboard(text: str) -> None:
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()
    root.destroy()


def build_html_page(token: str) -> str:
    return f"""\
<!DOCTYPE html>
<html>
<head>
  <title>Dataspot Facade API - Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui.css">
  <style>
    body {{ margin: 0; }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui-bundle.js"></script>
  <script>
    const ui = SwaggerUIBundle({{
      url: "{DOCS_SPEC_URL}",
      dom_id: '#swagger-ui',
      onComplete: function() {{
        ui.authActions.authorize({{
          HTTPBearer: {{
            name: "HTTPBearer",
            schema: {{type: "http", scheme: "bearer"}},
            value: "{token}"
          }}
        }});
      }}
    }});
  </script>
</body>
</html>"""


class _DocsHandler(SimpleHTTPRequestHandler):
    def __init__(self, html_content, *args, **kwargs):
        self._html_content = html_content
        super().__init__(*args, directory=None, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self._html_content.encode("utf-8"))

    def log_message(self, format, *args):
        pass


def main() -> None:
    access_key = os.environ.get("MY_DATASPOT_TOKEN")
    if not access_key:
        print("ERROR: MY_DATASPOT_TOKEN is not set. Check your .env file.")
        raise SystemExit(1)

    print(f"Authenticating with {AUTH_URL} ...")
    token = get_jwt_token(access_key)
    print(f"Token obtained: {token[:16]}...")

    copy_to_clipboard(token)
    print("Token copied to clipboard.")

    html = build_html_page(token)

    def handler(*a, **kw):
        return _DocsHandler(html, *a, **kw)

    server = HTTPServer(("127.0.0.1", DOCS_SERVER_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    docs_url = f"http://127.0.0.1:{DOCS_SERVER_PORT}"
    print(f"Opening docs at {docs_url} ...")
    webbrowser.open(docs_url)

    print("Press Ctrl+C to stop the docs server.")
    try:
        thread.join()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nDocs server stopped.")


if __name__ == "__main__":
    main()
