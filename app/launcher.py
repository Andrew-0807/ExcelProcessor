import socket
import subprocess
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import pystray
from PIL import Image
from werkzeug.serving import make_server

from scripts.app_info import APP_NAME, DEFAULT_HOST, DEFAULT_PORT
from app.server import app


def _resource_path(relative: str) -> Path:
    return Path(__file__).resolve().parent / relative


def _load_icon() -> Image.Image:
    icon_path_candidates = [
        Path("assets") / "icons" / "excel-processor-icon.png",
        Path("assets") / "icons" / "excel-processor-icon.ico",
        Path("static") / "excel-processor-icon.ico",
    ]
    for candidate in icon_path_candidates:
        full_path = _resource_path(str(candidate))
        if full_path.exists():
            return Image.open(full_path).copy()
    # Fall back to blank icon if nothing is available.
    return Image.new("RGBA", (64, 64), color=(102, 126, 234, 255))


def _open_interface() -> None:
    host = "127.0.0.1" if DEFAULT_HOST == "0.0.0.0" else DEFAULT_HOST
    webbrowser.open(f"http://{host}:{DEFAULT_PORT}")


def _lan_url() -> str:
    """Address other machines on the LAN should use. UDP connect() picks the
    interface with the default route without sending anything."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return f"http://{ip}:{DEFAULT_PORT}"


class TrayApplication:
    def __init__(self) -> None:
        # threaded: processing an Excel file takes seconds; without this one
        # user's upload blocks every other user on the network.
        self._server = make_server(DEFAULT_HOST, DEFAULT_PORT, app, threaded=True)
        self._icon: Optional[pystray.Icon] = None

    def _on_open(self, icon: pystray.Icon, item) -> None:  # noqa: U100
        _open_interface()

    def _on_copy_url(self, icon: pystray.Icon, item) -> None:  # noqa: U100
        subprocess.run("clip", input=_lan_url(), text=True, shell=True)

    def _on_exit(self, icon: pystray.Icon, item) -> None:  # noqa: U100
        icon.stop()

    def run(self) -> None:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        # Launch browser on first start to surface the UI.
        threading.Timer(1.5, _open_interface).start()

        lan = _lan_url()
        menu = pystray.Menu(
            pystray.MenuItem(f"Open {APP_NAME}", self._on_open),
            pystray.MenuItem(f"Network: {lan}", self._on_copy_url),
            pystray.MenuItem("Exit", self._on_exit),
        )
        icon = pystray.Icon("excel_transformer", _load_icon(), f"{APP_NAME} - {lan}", menu)
        self._icon = icon
        icon.run()

        self._server.shutdown()


def main() -> None:
    TrayApplication().run()


if __name__ == "__main__":
    main()
