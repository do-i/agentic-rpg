from __future__ import annotations

import argparse
import threading
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="map_editor", description="JRPG scenario map viewer/editor."
    )
    parser.add_argument(
        "--scenario",
        required=True,
        type=Path,
        help="Path to a scenario root (containing manifest.yaml), e.g. ./rusted_kingdoms",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the web editor (browser UI) instead of the pygame window.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8017,
        help="Port for the web editor backend (only with --web). Default: 8017.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open a browser tab automatically (only with --web).",
    )
    args = parser.parse_args()
    if args.web:
        _run_web(args.scenario, args.port, open_browser=not args.no_browser)
    else:
        from tools.map_editor.app import App

        App(args.scenario).run()


def _run_web(scenario_root: Path, port: int, open_browser: bool) -> None:
    try:
        import uvicorn
    except ImportError:
        raise SystemExit(
            "The web editor requires the 'editor' extras:\n"
            '    pip install -e ".[dev,editor]"'
        )
    from tools.map_editor.web.server import FRONTEND_DIST, create_app

    if not FRONTEND_DIST.is_dir():
        print(
            "Note: frontend not built — serving the API only.\n"
            "Build it once with:\n"
            "    cd tools/map_editor_web && npm install && npm run build"
        )
    app = create_app(scenario_root)
    url = f"http://127.0.0.1:{port}/"
    print(f"Map editor: {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
