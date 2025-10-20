"""Build a double-clickable macOS app bundle using PyInstaller."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "Lead Enricher"
BUNDLE_IDENTIFIER = "com.leadenricher.desktop"


def ensure_macos() -> None:
    if platform.system() != "Darwin":
        print("[warn] This helper is intended to be run on macOS.")


def run_pyinstaller(repo_root: Path) -> Path:
    launcher = repo_root / "mac_app" / "launch_lead_enricher.py"
    if not launcher.exists():
        raise SystemExit(f"Launcher script not found at {launcher}")

    dist_dir = repo_root / "dist"
    build_dir = repo_root / "build"
    for folder in (dist_dir, build_dir):
        if folder.exists():
            shutil.rmtree(folder)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        f"--name={APP_NAME}",
        f"--osx-bundle-identifier={BUNDLE_IDENTIFIER}",
        str(launcher),
    ]
    print("[info] Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    app_bundle = dist_dir / f"{APP_NAME}.app"
    if not app_bundle.exists():
        raise SystemExit("PyInstaller did not produce the expected .app bundle")
    return app_bundle


def zip_bundle(app_bundle: Path, repo_root: Path) -> Path:
    zip_path = repo_root / "Lead-Enricher-mac"
    if zip_path.with_suffix(".zip").exists():
        zip_path.with_suffix(".zip").unlink()
    archive = shutil.make_archive(str(zip_path), "zip", app_bundle.parent, app_bundle.name)
    print(f"[info] Created archive at {archive}")
    return Path(archive)


def main() -> None:
    ensure_macos()
    repo_root = Path(__file__).resolve().parents[1]
    app_bundle = run_pyinstaller(repo_root)
    print(f"[info] App bundle available at {app_bundle}")
    zip_bundle(app_bundle, repo_root)
    print("[done] Finder-ready app bundle created. Double-click to launch.")


if __name__ == "__main__":  # pragma: no cover - build orchestration
    main()
