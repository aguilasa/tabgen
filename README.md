# tabgen

Open source tool that takes a song's audio file and produces editable guitar/bass
tablature: it separates the instruments (electric guitar, acoustic guitar, bass),
detects the key, chords and tempo, and exports the result as Guitar Pro (`.gp5`),
MusicXML, MIDI and ASCII tab — using only free and open models.

tabgen is CLI-first and layered: a pure-Python core library (`tabgen/core`) does
all the work, and thin interfaces (the CLI today, possibly web/desktop later)
consume its API.

> Status: early development. See [docs/planejamento/audio-para-tablatura.md](docs/planejamento/audio-para-tablatura.md)
> for the full research and planning document (in Brazilian Portuguese).

## How it works

Six-stage pipeline, all stages behind a pure-Python core library:

1. **Source separation** — [Demucs v4](https://github.com/adefossez/demucs) (`htdemucs_ft` + `htdemucs_6s`)
2. **Key + chord detection** — [madmom](https://github.com/CPJKU/madmom)
3. **Beat / downbeat tracking** — madmom `DBNDownBeatTracker` (bar grid + BPM)
4. **Audio-to-notes transcription** — [Basic Pitch](https://github.com/spotify/basic-pitch) per stem
5. **String/fret assignment** — dynamic programming over fingering costs (configurable tuning)
6. **Quantization + export** — [music21](https://www.music21.org) + [PyGuitarPro](https://github.com/Perlence/PyGuitarPro) (`.gp5`)

## Architecture

```
tabgen/
├── core/        # pure library: no terminal, HTTP or GUI I/O
│   ├── separation/  analysis/  transcription/  fretting/  export/
│   ├── models.py    # serializable dataclasses (stage contracts)
│   ├── cache.py     # on-disk cache of stage results
│   └── pipeline.py  # orchestration, progress via callbacks
└── cli/         # thin layer (v1); web/ and desktop/ may come later
```

The core never prints or serves HTTP; interfaces are thin consumers of its API,
so the CLI can later be joined by a web or desktop front end without rewriting
the pipeline. Stage results are JSON-serializable and cached on disk.

## Requirements

- Linux
- Python 3.10–3.11 (upper bound set by the madmom dependency)
- ffmpeg on the `PATH`
- NVIDIA GPU with ≥6 GB VRAM recommended; CPU works but is 10–20× slower

## Installation

From a clone of this repository:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**PyTorch / CUDA note:** the default `pip install torch` (which the command
above runs for you) pulls the CUDA-enabled Linux wheel from PyPI. If you need a
build for a specific CUDA version, install torch from the PyTorch index instead,
e.g.:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

(replace `cu121` with the CUDA version you want — see
[pytorch.org](https://pytorch.org/get-started/locally/) for the available tags).

## Usage

Check the installed version:

```bash
tabgen --version
```

Check that your environment can run tabgen (ffmpeg, Python version,
torch + CUDA/GPU, free disk space). Exit code is 0 when all essential checks
pass:

```bash
tabgen doctor
```

Machine-readable output:

```bash
tabgen doctor --json
```

The pipeline commands (separation, transcription, export) are under
development.

## Development

Run the test suite and the linter from the repository root:

```bash
pytest -q
ruff check .
```

Layering rule enforced by ruff and by review: `tabgen/core/` must stay a pure
library — no `print`, no `typer`/`rich` imports; terminal output lives only in
`tabgen/cli/`.

## License

The tabgen code is licensed under the [MIT License](LICENSE).

Third-party model weights keep their own licenses, and some are
**non-commercial**: madmom models are CC BY-NC-SA 4.0 and the Demucs
pre-trained weights carry research-oriented, non-commercial terms. tabgen is
therefore suitable for personal / free use; check those licenses before any
commercial use. See the planning document for details.
