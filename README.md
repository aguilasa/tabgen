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
- git and a C compiler (gcc) at install time — madmom is built from source
- NVIDIA GPU with ≥6 GB VRAM recommended; CPU works but is 10–20× slower

## Installation

From a clone of this repository:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install --no-deps basic-pitch==0.4.0
```

The last step is required: Basic Pitch is installed with `--no-deps` because its
wheel metadata pulls in tensorflow, which forces numpy<2 and conflicts with the
torch stack — tabgen uses its ONNX backend, whose actual dependencies
(onnxruntime, librosa, pretty-midi, ...) are already listed in `pyproject.toml`.
Without this step the `transcribe` command will not work.

**madmom note:** `pip install -e ".[dev]"` installs madmom from a pinned commit
of the [CPJKU/madmom](https://github.com/CPJKU/madmom) GitHub repository (no
extra step needed). The last PyPI release (0.16.1, from 2018) does not build on
Python 3.11 / numpy 2, while upstream HEAD does — without downgrading numpy or
torch. Because it is built from source, git and a C compiler must be available
at install time.

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
torch + CUDA/GPU, madmom, free disk space). Exit code is 0 when all essential
checks pass:

```bash
tabgen doctor
```

Machine-readable output:

```bash
tabgen doctor --json
```

### Separate a song into stems

```bash
tabgen separate song.mp3
```

Runs Demucs (`htdemucs_ft` + `htdemucs_6s`) and writes
`stems/{vocals,drums,bass,other,guitar}.wav` next to the input. Use
`--device cuda|cpu` to override the autodetected device.

### Transcribe a song to MIDI

```bash
tabgen transcribe song.mp3
```

Runs the full Phase 1 pipeline: separation, then Basic Pitch transcription of
each stem, then MIDI export. It writes one Standard MIDI File per instrument —
`song.guitar.mid` and `song.bass.mid` by default — next to the input (override
with `--output-dir`). Options:

- `--instruments guitar,bass` — comma-separated subset of `guitar`, `bass`.
- `--output-dir DIR` — where the `.mid` files go.
- `--device cuda|cpu` — device for Demucs (default: autodetect).

Each `.mid` file contains a single track with the detected notes (pitch, onset,
duration, velocity) plus the pitch bends Basic Pitch reports, under a General
MIDI program (steel guitar / fingered bass). Timestamps are absolute seconds —
no quantization to a bar grid yet (that is a later pipeline stage). The files
open in any MIDI player or editor; [TuxGuitar](https://tuxguitar.app) is the
reference target, since it shows them directly as tablature.

**Caching:** stage results are cached in `.tabgen/` directories next to the
audio files (keyed by content hash, model and parameters). Re-running a command
on an unchanged input reuses the cache and finishes in under a second — delete
the `.tabgen/` directories (and `stems/`) to force a re-run.

### Analyze a song (key, tempo, chords)

```bash
tabgen analyze song.mp3
```

Runs the Phase 2 pipeline: separation (reusing the cache when warm), then
madmom beat/downbeat tracking on the original audio and key/chord recognition
on a drum-free mix of the stems. It prints a report and writes
`song.analysis.json` next to the input (override with `--output`):

```text
Key: F# major (confidence 0.86)
Tempo: 139.5 BPM (580 beats, 145 downbeats)
Chords:
     1.60s -    5.30s  F#:maj
     5.30s -    8.80s  B:maj
     8.80s -   12.20s  D#:min
     ...
```

Chord labels use the [Harte](https://ismir2005.ismir.net/proceedings/1080.pdf)
syntax (`F#:maj`, `D#:min`, `N` for no chord). The JSON file is an
`AnalysisResult` (key, confidence, BPM, beat/downbeat times, chord segments)
that later pipeline stages consume. Options:

- `--output FILE` — where the JSON report goes.
- `--device cuda|cpu` — device for Demucs (default: autodetect).

### Expected runtimes

Indicative numbers on a 6 GB NVIDIA GPU (RTX 3060 Laptop), measured with a
synthetic 10-second sample and with a real 4 min 08 s song during the Phase 1
end-to-end validation:

| Scenario                              | Time            |
| ------------------------------------- | --------------- |
| `transcribe`, cold (no cache)         | ~10 s (≈5 s separation, ≈2 s transcription + export) |
| `transcribe`, warm (cache hit)        | < 1 s           |
| 4-minute song, cold (no cache)        | ~61 s total (≈47 s separation, ≈6 s guitar + ≈4 s bass transcription) |
| 4-minute song, warm (cache hit)       | ~1.5 s          |
| `analyze`, 4-minute song, cold        | ~140 s total (≈45 s separation, ≈27 s beats, ≈64 s key + chords; madmom runs on CPU) |
| `analyze`, 4-minute song, warm        | < 1 s           |

The very first run also downloads the Demucs model weights (~1 GB). On CPU,
expect separation to be 10–20× slower.

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
