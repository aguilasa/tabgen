# tabgen Studio

Desktop front end for tabgen (Tauri 2 + React + Vite). It holds no musical
logic: every job runs `python -m tabgen.worker` from an existing tabgen install
and shows the worker's progress and results (protocol:
[`tabgen/worker/__init__.py`](../tabgen/worker/__init__.py)).

The app does **not** bundle Python or the models. It needs tabgen installed in
a virtual environment, as described in the [root README](../README.md#installation).

## Requirements to run

- Linux with the WebKitGTK 4.1 runtime (`libwebkit2gtk-4.1-0`, `libgtk-3-0`;
  the `.deb` declares them)
- `ffmpeg` and `ffprobe` on the `PATH`
- A Python 3.10–3.11 virtual environment where `pip install -e ".[dev]"` was run
  from a clone of this repository (see the root README). The app checks it on
  the **Ambiente** screen.

## Where the app finds Python

**Ambiente → Padrões da interface → Interpretador Python** holds the path of the
interpreter the worker runs with, e.g. `/home/you/tabgen/.venv/bin/python`.
Left empty, it uses `.venv/bin/python` of the checkout the app was built from.
That default only exists on the build machine, so set the field anywhere else.

When the path does not exist, or `tabgen` is not installed in that interpreter,
the app still opens: the header shows "Ambiente com falha" and the Ambiente
screen says what is missing and how to fix it.

The first tablature run downloads the model weights (Demucs ~1 GB, riley
~99 MB) into the user's cache; later runs reuse them.

## Development

Toolchain: Node 20 and Rust stable. This repository is used with
[mise](https://mise.jdx.dev/) (`mise use -g node@20 rust@stable`); any install
of the same versions works. System packages for building Tauri on
Debian/Ubuntu:

```bash
sudo apt install libwebkit2gtk-4.1-dev librsvg2-dev libxdo-dev \
  libayatana-appindicator3-dev libssl-dev build-essential file
```

```bash
cd desktop
npm install          # .npmrc sets legacy-peer-deps
npm run tauri dev    # Vite on :1420 + the app window
npm run typecheck
```

## Building the Linux bundles

```bash
cd desktop
npm run tauri build
```

Output, in `desktop/src-tauri/target/release/bundle/`:

| Bundle | File | Size |
|---|---|---|
| Debian package | `deb/tabgen-studio_0.1.0_amd64.deb` | 1.9 MiB |
| AppImage | `appimage/tabgen-studio_0.1.0_amd64.AppImage` | 80 MiB |

The AppImage carries its own WebKitGTK, hence the size. Building it needs
network access the first time: the bundler downloads `linuxdeploy` and its
AppImage plugin. A release build took 274 s on the development machine
(first run, including that download) and 202 s afterwards.

Install or run:

```bash
sudo apt install ./desktop/src-tauri/target/release/bundle/deb/tabgen-studio_0.1.0_amd64.deb
# or
chmod +x tabgen-studio_0.1.0_amd64.AppImage && ./tabgen-studio_0.1.0_amd64.AppImage
```

Inside an AppImage, AppRun points `PYTHONHOME`, `LD_LIBRARY_PATH`, `GTK_*` and
similar variables into the mounted image. The app removes them before starting
Python, `ffprobe` or `xdg-open`, so the worker sees the same environment as
from a terminal.

Out of scope for v1: CI, Windows/macOS installers and bundling Python.
