#!/usr/bin/env python3
"""Validate and test the exact Pages artifact at a /Vellum/ project subpath."""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-browser", action="store_true", help="Only check syntax and build")
    parser.add_argument(
        "--subpath",
        default=None,
        help="Project subpath for Pages testing (defaults to GITHUB_REPOSITORY repo name or 'Vellum')",
    )
    args = parser.parse_args()
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for JavaScript syntax validation")
    for source in sorted((ROOT / "src").glob("*.js")):
        run(node, "--check", str(source))
    for source in [ROOT / "build.py", *sorted((ROOT / "scripts").glob("*.py")), ROOT / "tests/smoke.py"]:
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
    run(sys.executable, "scripts/build_site.py")
    if args.skip_browser:
        return

    repo_subpath = args.subpath
    if not repo_subpath:
        env_repo = os.environ.get("GITHUB_REPOSITORY", "")
        repo_subpath = env_repo.split("/")[-1] if env_repo else "Vellum"
    repo_subpath = repo_subpath.strip("/") or "Vellum"

    with tempfile.TemporaryDirectory(prefix="vellum-ci-") as tmp:
        shutil.copytree(ROOT / "_site", Path(tmp) / repo_subpath)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/{repo_subpath}/?canvas"
            run(sys.executable, "tests/smoke.py", "--url", url,
                "--expect-backend", "Canvas 2D", "--output-dir", "test-results")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
