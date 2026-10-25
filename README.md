# tabgen

Open source tool that takes a song's audio file and produces editable guitar/bass
tablature: it separates the instruments (electric guitar, acoustic guitar, bass),
detects the key, chords and tempo, and exports the result as Guitar Pro (`.gp5`),
MusicXML, MIDI and ASCII tab — using only free and open models.

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
│   └── pipeline.py  # orchestration, progress via callbacks
└── cli/         # thin layer (v1); web/ and desktop/ may come later
```

The core never prints or serves HTTP; interfaces are thin consumers of its API,
so the CLI can later be joined by a web or desktop front end without rewriting
the pipeline. Stage results are JSON-serializable and cached on disk.

## Requirements

- Linux, Python 3.10–3.11, ffmpeg
- NVIDIA GPU (≥6 GB VRAM) recommended; CPU works but is 10–20× slower

## Expectations

Automatic transcription is not perfect (state of the art is roughly 66% note
F-measure on real recordings, ~54% end-to-end tab F1). tabgen produces a good
**editable draft** to review in TuxGuitar or Guitar Pro — not a final score.

## License

MIT (code). Third-party model weights keep their own licenses — notably madmom
models (CC BY-NC-SA 4.0, non-commercial) and Demucs weights (research-oriented
terms). See the planning document for details.
