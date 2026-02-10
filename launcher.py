from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

import pystray
from PIL import Image
from werkzeug.serving import make_server

from app_info import (
    APP_NAME,
    DEFAULT_HOST,
    DEFAULT_PORT,
    UPDATE_CHECK_INTERVAL,
)
from auto_update import AutoUpdateError, run_auto_update
from server import create_app


class _ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self._app = create_app()
        self._server = make_server(host, port, self._app)
        self._ctx = self._app.app_context()
        self._ctx.push()

    def run(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()
        self._ctx.pop()


def _resource_path(relative: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative


def _load_icon() -> Image.Image:
    icon_path_candidates = [
        Path("static") / "excel-processor-icon.ico",
        Path("excel-processor-icon.ico"),
        Path("static") / "Treetog-Junior-Document-excel.ico",
        Path("Treetog-Junior-Document-excel.ico"),
    ]
    for candidate in icon_path_candidates:
        full_path = _resource_path(str(candidate))
        if full_path.exists():
            return Image.open(full_path).copy()
    # Fall back to blank icon if nothing is available.
    return Image.new("RGBA", (64, 64), color=(102, 126, 234, 255))


def _open_interface() -> None:
    webbrowser.open(f"http://{DEFAULT_HOST}:{DEFAULT_PORT}")


class TrayApplication:
    def __init__(self) -> None:
        self._server_thread = _ServerThread(DEFAULT_HOST, DEFAULT_PORT)
        self._icon: Optional[pystray.Icon] = None
        self._should_restart = False
        self._exit_event = threading.Event()

    # region Tray menu callbacks
    def _on_open(self, icon: pystray.Icon, item) -> None:  # noqa: U100
        _open_interface()

    def _on_exit(self, icon: pystray.Icon, item) -> None:  # noqa: U100
        self._exit_event.set()
        icon.stop()

    def _on_check_updates(self, icon: pystray.Icon, item) -> None:  # noqa: U100
        threading.Thread(target=self._perform_manual_update, daemon=True).start()

    # endregion

    def _perform_manual_update(self) -> None:
        if self._icon is None:
            return
        try:
            result = run_auto_update()
        except AutoUpdateError as exc:
            self._notify(f"Update failed: {exc}")
            return

        if result is None:
            self._notify("Already on the latest version.")
            return

        self._should_restart = True
        self._notify(f"Updating to version {result.version}. Restarting...")
        self._request_exit()

    def _auto_update_worker(self) -> None:
        # Give the UI a moment to come up before we start network requests.
        time.sleep(5)
        while not self._exit_event.is_set():
            if self._icon is None or not self._icon.visible:
                time.sleep(1)
                continue
            try:
                result = run_auto_update()
            except AutoUpdateError as exc:
                self._notify(f"Auto-update failed: {exc}")
                return

            if result is not None:
                self._should_restart = True
                self._notify(f"Update {result.version} downloaded. Restarting...")
                self._request_exit()
                return

            if UPDATE_CHECK_INTERVAL <= 0:
                return
            time.sleep(UPDATE_CHECK_INTERVAL)

    def _request_exit(self) -> None:
        self._exit_event.set()
        if self._icon is not None:
            self._icon.stop()

    def _notify(self, message: str) -> None:
        if self._icon is None:
            return
        try:
            self._icon.notify(message, APP_NAME)
        except Exception:
            # Notifications are best-effort only.
            pass

    def run(self) -> None:
        self._server_thread.start()
        # Launch browser on first start to surface the UI.
        threading.Timer(1.5, _open_interface).start()

        menu = pystray.Menu(
            pystray.MenuItem(f"Open {APP_NAME}", self._on_open),
            pystray.MenuItem("Check for updates", self._on_check_updates),
            pystray.MenuItem("Exit", self._on_exit),
        )
        icon = pystray.Icon("excel_transformer", _load_icon(), APP_NAME, menu)
        self._icon = icon

        threading.Thread(target=self._auto_update_worker, daemon=True).start()
        icon.run()

        self._server_thread.shutdown()
        if self._should_restart:
            # Allow the update helper script to take over.
            os._exit(0)


def main() -> None:
    TrayApplication().run()


if __name__ == "__main__":
    main()
