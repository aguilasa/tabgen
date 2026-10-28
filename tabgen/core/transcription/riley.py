"""Guitar transcription with the Riley et al. CRNN, bends from Basic Pitch.

Model: "High Resolution Guitar Transcription via Domain Adaptation" (Riley,
Edwards & Dixon, ICASSP 2024) and its GAPS training (Riley et al., ISMIR
2024): the high-resolution CRNN of Kong et al. (onset/offset regression,
frame and velocity heads) trained on guitar. Checkpoint ``guitar-gaps.pth``
from https://huggingface.co/xavriley/midi-transcription-models (MIT), pinned
to one revision and checked against its sha256.

The network definition (:class:`RegressOnsetOffsetFrameVelocityCRNN` and its
blocks) and the regression post-processing (:func:`_binarize_regression`,
:func:`_detect_notes`) are rewritten from Kong et al., "High-resolution
Piano Transcription with Pedals by Regressing Onset and Offset Times",
https://github.com/qiuqiangkong/piano_transcription (MIT License,
Copyright (c) 2020 Qiuqiang Kong), keeping its layer names (the checkpoint's
state-dict keys) and its numerics. Inference settings follow the reference
used for the evaluation (16 kHz, 100 frames/s, 10 s segments with 50 %
overlap, thresholds onset 0.3 / offset 0.3 / frame 0.1). The log-mel front
end is ``torchlibrosa`` (MIT), the library the checkpoint was trained with.

The Riley model outputs no pitch-bend curve, so the result is hybrid: Basic
Pitch also transcribes the same stem and every Riley note takes the
``bends`` of the Basic Pitch note with the same pitch whose onset is within
:data:`BEND_MATCH_TOLERANCE_S` (one-to-one, nearest onset first). Unmatched
notes keep ``bends=None``. The technique detectors then run on this result.

This module is pure core: no stdout/typer/rich. Heavy libraries (torch,
torchlibrosa, librosa, huggingface_hub) load on first use.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Sequence

from tabgen.core.cache import StageCache
from tabgen.core.models import NOTE_CONTRACT_REVISION, Note, NoteEvents
from tabgen.core.pipeline import ProgressCallback, null_progress
from tabgen.core.transcription import basic_pitch
from tabgen.core.transcription.basic_pitch import (
    TranscriptionError,
    TranscriptionResult,
)

STAGE = "transcription"

# Pinned checkpoint (huggingface_hub cache, downloaded on first use).
WEIGHTS_REPO_ID = "xavriley/midi-transcription-models"
WEIGHTS_FILENAME = "guitar-gaps.pth"
WEIGHTS_REVISION = "b7bec65a2b860aca72856b0feef58b5df407b777"
WEIGHTS_SHA256 = "65483e7c0e340a90415b15b520687587698c8c728f5fa470a205f13ee45c6513"
MODEL_NAME = "riley-guitar-gaps"
MODEL_VERSION = f"{MODEL_NAME}@sha256:{WEIGHTS_SHA256[:12]}"

# Kong et al. front end and output layout.
SAMPLE_RATE = 16000
FRAMES_PER_SECOND = 100
CLASSES_NUM = 88
BEGIN_NOTE = 21  # MIDI pitch of class 0 (A0)
SEGMENT_SECONDS = 10
BATCH_SIZE = 8

# Post-processing thresholds (reference inference defaults).
ONSET_THRESHOLD = 0.3
OFFSET_THRESHOLD = 0.3
FRAME_THRESHOLD = 0.1
ONSET_NEIGHBOUR = 2
OFFSET_NEIGHBOUR = 4
MAX_NOTE_FRAMES = 600  # a note without detected offset ends after 6 s

# Riley note <-> Basic Pitch note onset tolerance for copying bends; the
# same 50 ms as the evaluation's onset criterion (scripts/eval/metrics.py).
BEND_MATCH_TOLERANCE_S = 0.05

INSTRUMENTS = ("guitar",)

# Raw Riley note: (onset_s, offset_s, pitch_midi, velocity in [0, 1]).
RawRileyNote = tuple[float, float, int, float]

# Runs the Riley model on an audio file. Injectable for tests.
Predictor = Callable[[Path], list[RawRileyNote]]
# Basic Pitch transcription used for the bends (same signature as
# basic_pitch.transcribe). Injectable for tests.
BendTranscribeFn = Callable[..., tuple[TranscriptionResult, bool]]


def transcription_version(instrument: str = "guitar") -> str:
    """Cache version of the hybrid transcription for one instrument.

    Pins the Riley weights (sha prefix), the Basic Pitch model that gives
    the bends, the matching tolerance and the Note contract revision.
    """
    tolerance_ms = round(BEND_MATCH_TOLERANCE_S * 1000)
    return (
        f"{MODEL_VERSION}-{instrument}+bends-{basic_pitch.MODEL_VERSION}"
        f"-tol{tolerance_ms}ms+note-{NOTE_CONTRACT_REVISION}"
    )


# --------------------------------------------------------------------------
# Weights


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hf_download() -> Path:
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            WEIGHTS_REPO_ID, WEIGHTS_FILENAME, revision=WEIGHTS_REVISION
        )
    )


def weights_path(download: Callable[[], Path] = _hf_download) -> Path:
    """Local path of the pinned checkpoint, verified against its sha256."""
    try:
        path = Path(download())
    except Exception as err:  # network/hub errors: surface as stage error
        raise TranscriptionError(
            f"cannot fetch {WEIGHTS_FILENAME} from {WEIGHTS_REPO_ID}: {err}"
        ) from err
    actual = _sha256(path)
    if actual != WEIGHTS_SHA256:
        raise TranscriptionError(
            f"{path} has sha256 {actual}, expected {WEIGHTS_SHA256}"
        )
    return path


# --------------------------------------------------------------------------
# Network (Kong et al., Regress_onset_offset_frame_velocity_CRNN)


def _torch_modules() -> dict[str, Any]:
    """Build the nn.Module classes (torch is imported only when needed)."""
    import torch
    import torch.nn.functional as F
    from torch import nn
    from torchlibrosa.stft import LogmelFilterBank, Spectrogram

    class ConvBlock(nn.Module):
        def __init__(self, in_channels: int, out_channels: int, momentum: float):
            super().__init__()
            self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=(3, 3),
                                   stride=(1, 1), padding=(1, 1), bias=False)
            self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=(3, 3),
                                   stride=(1, 1), padding=(1, 1), bias=False)
            self.bn1 = nn.BatchNorm2d(out_channels, momentum)
            self.bn2 = nn.BatchNorm2d(out_channels, momentum)

        def forward(self, x, pool_size=(1, 2)):
            x = F.relu_(self.bn1(self.conv1(x)))
            x = F.relu_(self.bn2(self.conv2(x)))
            return F.avg_pool2d(x, kernel_size=pool_size)

    class AcousticModelCRnn8Dropout(nn.Module):
        def __init__(self, classes_num: int, midfeat: int, momentum: float):
            super().__init__()
            self.conv_block1 = ConvBlock(1, 48, momentum)
            self.conv_block2 = ConvBlock(48, 64, momentum)
            self.conv_block3 = ConvBlock(64, 96, momentum)
            self.conv_block4 = ConvBlock(96, 128, momentum)
            self.fc5 = nn.Linear(midfeat, 768, bias=False)
            self.bn5 = nn.BatchNorm1d(768, momentum=momentum)
            self.gru = nn.GRU(input_size=768, hidden_size=256, num_layers=2,
                              bias=True, batch_first=True, dropout=0.0,
                              bidirectional=True)
            self.fc = nn.Linear(512, classes_num, bias=True)

        def forward(self, x):
            # Inference only: dropout layers of the original are identities.
            x = self.conv_block1(x)
            x = self.conv_block2(x)
            x = self.conv_block3(x)
            x = self.conv_block4(x)
            x = x.transpose(1, 2).flatten(2)
            x = F.relu(self.bn5(self.fc5(x).transpose(1, 2)).transpose(1, 2))
            x, _ = self.gru(x)
            return torch.sigmoid(self.fc(x))

    class RegressOnsetOffsetFrameVelocityCRNN(nn.Module):
        def __init__(self, classes_num: int = CLASSES_NUM):
            super().__init__()
            window_size = 2048
            mel_bins = 229
            midfeat = 1792
            momentum = 0.01
            self.spectrogram_extractor = Spectrogram(
                n_fft=window_size, hop_length=SAMPLE_RATE // FRAMES_PER_SECOND,
                win_length=window_size, window="hann", center=True,
                pad_mode="reflect", freeze_parameters=True,
            )
            self.logmel_extractor = LogmelFilterBank(
                sr=SAMPLE_RATE, n_fft=window_size, n_mels=mel_bins, fmin=30,
                fmax=SAMPLE_RATE // 2, ref=1.0, amin=1e-10, top_db=None,
                freeze_parameters=True,
            )
            self.bn0 = nn.BatchNorm2d(mel_bins, momentum)
            self.frame_model = AcousticModelCRnn8Dropout(classes_num, midfeat, momentum)
            self.reg_onset_model = AcousticModelCRnn8Dropout(
                classes_num, midfeat, momentum
            )
            self.reg_offset_model = AcousticModelCRnn8Dropout(
                classes_num, midfeat, momentum
            )
            self.velocity_model = AcousticModelCRnn8Dropout(
                classes_num, midfeat, momentum
            )
            self.reg_onset_gru = nn.GRU(input_size=classes_num * 2, hidden_size=256,
                                        num_layers=1, bias=True, batch_first=True,
                                        dropout=0.0, bidirectional=True)
            self.reg_onset_fc = nn.Linear(512, classes_num, bias=True)
            self.frame_gru = nn.GRU(input_size=classes_num * 3, hidden_size=256,
                                    num_layers=1, bias=True, batch_first=True,
                                    dropout=0.0, bidirectional=True)
            self.frame_fc = nn.Linear(512, classes_num, bias=True)

        def forward(self, waveform):
            x = self.spectrogram_extractor(waveform)  # (batch, 1, time, freq)
            x = self.logmel_extractor(x)  # (batch, 1, time, mel)
            x = self.bn0(x.transpose(1, 3)).transpose(1, 3)

            frame_output = self.frame_model(x)
            reg_onset_output = self.reg_onset_model(x)
            reg_offset_output = self.reg_offset_model(x)
            velocity_output = self.velocity_model(x)

            # Velocities condition the onset regression.
            x = torch.cat(
                (reg_onset_output, (reg_onset_output ** 0.5) * velocity_output),
                dim=2,
            )
            x, _ = self.reg_onset_gru(x)
            reg_onset_output = torch.sigmoid(self.reg_onset_fc(x))

            # Onsets and offsets condition the frame-wise classification.
            x = torch.cat((frame_output, reg_onset_output, reg_offset_output), dim=2)
            x, _ = self.frame_gru(x)
            frame_output = torch.sigmoid(self.frame_fc(x))
            return {
                "reg_onset_output": reg_onset_output,
                "reg_offset_output": reg_offset_output,
                "frame_output": frame_output,
                "velocity_output": velocity_output,
            }

    return {"RegressOnsetOffsetFrameVelocityCRNN": RegressOnsetOffsetFrameVelocityCRNN}


def build_model():
    """An untrained network with the checkpoint's architecture and key names."""
    return _torch_modules()["RegressOnsetOffsetFrameVelocityCRNN"]()


def default_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=2)
def load_model(device: str):
    """Load the pinned checkpoint on ``device`` (cached per device)."""
    import torch

    path = weights_path()
    # The checkpoint also pickles the training sampler state (numpy arrays),
    # which weights_only=True rejects; the file's sha256 is verified above.
    checkpoint = torch.load(str(path), map_location=device, weights_only=False)
    model = build_model()
    model.load_state_dict(checkpoint["model"], strict=True)
    model.to(device)
    model.eval()
    return model


# --------------------------------------------------------------------------
# Inference: segments in, frame-wise outputs out


def _enframe(audio, segment_samples: int):
    """Split padded audio (1, n) into segments overlapping by half."""
    import numpy as np

    assert audio.shape[1] % segment_samples == 0
    batch = []
    pointer = 0
    while pointer + segment_samples <= audio.shape[1]:
        batch.append(audio[:, pointer: pointer + segment_samples])
        pointer += segment_samples // 2
    return np.concatenate(batch, axis=0)


def _deframe(x):
    """Stitch per-segment outputs (N, frames, classes) back to (frames, classes).

    Keeps the middle half of inner segments (the first segment's first 3/4,
    the last segment's last 3/4) after dropping the extra frame that
    ``center=True`` adds at the end of each segment.
    """
    import numpy as np

    if x.shape[0] == 1:
        return x[0]
    x = x[:, 0:-1, :]
    n, frames, _ = x.shape
    assert frames % 4 == 0
    parts = [x[0, 0: int(frames * 0.75)]]
    for i in range(1, n - 1):
        parts.append(x[i, int(frames * 0.25): int(frames * 0.75)])
    parts.append(x[-1, int(frames * 0.25):])
    return np.concatenate(parts, axis=0)


def frame_outputs(model, audio, batch_size: int = BATCH_SIZE) -> dict[str, Any]:
    """Run ``model`` over mono 16 kHz ``audio``; frame-wise outputs per head.

    ``model`` maps a (batch, samples) float tensor to the four
    (batch, frames, classes) heads; any torch module with that contract
    works (tests inject a fake one).
    """
    import numpy as np
    import torch

    segment_samples = SEGMENT_SECONDS * SAMPLE_RATE
    audio = np.asarray(audio)[None, :]
    audio_len = audio.shape[1]
    pad_len = int(np.ceil(audio_len / segment_samples)) * segment_samples - audio_len
    audio = np.concatenate((audio, np.zeros((1, pad_len))), axis=1)
    segments = _enframe(audio, segment_samples)

    try:
        device = next(model.parameters()).device
    except StopIteration:
        device = torch.device("cpu")
    collected: dict[str, list] = {}
    with torch.no_grad():
        for start in range(0, len(segments), batch_size):
            batch = torch.tensor(
                segments[start: start + batch_size], dtype=torch.float32
            ).to(device)
            for key, value in model(batch).items():
                collected.setdefault(key, []).append(value.detach().cpu().numpy())
    return {
        key: _deframe(np.concatenate(values, axis=0))
        for key, values in collected.items()
    }


# --------------------------------------------------------------------------
# Post-processing (Kong et al., RegressionPostProcessor), vectorized where
# the result is identical to the per-frame loops of the original.


def _binarize_regression(reg_output, threshold: float, neighbour: int):
    """Peaks of a regression curve and their sub-frame shifts.

    A frame ``n`` (``neighbour <= n < frames - neighbour``) is a peak when
    its value exceeds ``threshold`` and the curve is non-decreasing over the
    ``neighbour`` frames before it and non-increasing over the ones after.
    The shift interpolates the peak position between neighbouring frames.
    """
    import numpy as np

    x = reg_output
    frames = x.shape[0]
    binary = np.zeros_like(x)
    shift = np.zeros_like(x)
    if frames <= 2 * neighbour:
        return binary, shift
    n = np.arange(neighbour, frames - neighbour)
    peak = x[n] > threshold
    for i in range(neighbour):
        peak &= ~(x[n - i] < x[n - i - 1])
        peak &= ~(x[n + i] < x[n + i + 1])
    rows, cols = np.nonzero(peak)
    rows = rows + neighbour
    prev, cur, nxt = x[rows - 1, cols], x[rows, cols], x[rows + 1, cols]
    with np.errstate(divide="ignore", invalid="ignore"):
        shift_values = np.where(
            prev > nxt, (nxt - prev) / (cur - nxt) / 2, (nxt - prev) / (cur - prev) / 2
        )
    binary[rows, cols] = 1
    shift[rows, cols] = shift_values
    return binary, shift


def _detect_note_frames(frame_output, onset_output, onset_shift_output,
                        offset_output, offset_shift_output, velocity_output,
                        frame_threshold: float) -> list[list[float]]:
    """Notes of one pitch: ``[onset_frame, offset_frame, onset_shift,
    offset_shift, velocity]``, by onset, as in Kong et al.

    Note: as in the original, an onset at frame 0 is treated as "no note
    open" (``if bgn``), which is kept for numerical equivalence.
    """
    output = []
    bgn = None
    frame_disappear = None
    offset_occur = None
    last = onset_output.shape[0] - 1
    for i in range(onset_output.shape[0]):
        if onset_output[i] == 1:
            if bgn:
                # Consecutive onsets: close the open note just before this one.
                fin = max(i - 1, 0)
                output.append([bgn, fin, onset_shift_output[bgn], 0,
                               velocity_output[bgn]])
                frame_disappear, offset_occur = None, None
            bgn = i
        if bgn and i > bgn:
            if frame_output[i] <= frame_threshold and not frame_disappear:
                frame_disappear = i
            if offset_output[i] == 1 and not offset_occur:
                offset_occur = i
            if frame_disappear:
                if offset_occur and offset_occur - bgn > frame_disappear - offset_occur:
                    fin = offset_occur
                else:
                    fin = frame_disappear
                output.append([bgn, fin, onset_shift_output[bgn],
                               offset_shift_output[fin], velocity_output[bgn]])
                bgn, frame_disappear, offset_occur = None, None, None
            if bgn and (i - bgn >= MAX_NOTE_FRAMES or i == last):
                fin = i
                output.append([bgn, fin, onset_shift_output[bgn],
                               offset_shift_output[fin], velocity_output[bgn]])
                bgn, frame_disappear, offset_occur = None, None, None
    output.sort(key=lambda row: row[0])
    return output


def outputs_to_notes(outputs: dict[str, Any]) -> list[RawRileyNote]:
    """Frame-wise model outputs -> ``(onset_s, offset_s, pitch, velocity)``."""
    import numpy as np

    onset, onset_shift = _binarize_regression(
        outputs["reg_onset_output"], ONSET_THRESHOLD, ONSET_NEIGHBOUR
    )
    offset, offset_shift = _binarize_regression(
        outputs["reg_offset_output"], OFFSET_THRESHOLD, OFFSET_NEIGHBOUR
    )
    frame = outputs["frame_output"]
    velocity = outputs["velocity_output"]
    rows: list[list[float]] = []
    pitches: list[int] = []
    for k in range(frame.shape[-1]):
        if not onset[:, k].any():
            continue  # no onset, no note (cheap skip of the frame loop)
        found = _detect_note_frames(
            frame[:, k], onset[:, k], onset_shift[:, k], offset[:, k],
            offset_shift[:, k], velocity[:, k], FRAME_THRESHOLD,
        )
        rows += found
        pitches += [k + BEGIN_NOTE] * len(found)
    if not rows:
        return []
    table = np.array(rows)
    onsets = (table[:, 0] + table[:, 2]) / FRAMES_PER_SECOND
    offsets = (table[:, 1] + table[:, 3]) / FRAMES_PER_SECOND
    stacked = np.stack(
        (onsets, offsets, np.array(pitches), table[:, 4]), axis=-1
    ).astype(np.float32)
    return [
        (float(on), float(off), int(pitch), float(vel))
        for on, off, pitch, vel in stacked
    ]


def predict(audio_path: Path, device: str | None = None) -> list[RawRileyNote]:
    """Run the pinned Riley model on an audio file (loaded at 16 kHz mono)."""
    import librosa

    model = load_model(device or default_device())
    samples, _ = librosa.load(str(audio_path), sr=SAMPLE_RATE, mono=True)
    return outputs_to_notes(frame_outputs(model, samples))


# --------------------------------------------------------------------------
# Hybrid result


def merge_bends(
    notes: Sequence[Note],
    bend_notes: Sequence[Note],
    tolerance_s: float = BEND_MATCH_TOLERANCE_S,
) -> list[Note]:
    """Copy ``bends`` from ``bend_notes`` onto matching ``notes`` (in place).

    A pair matches when both notes have the same pitch and their onsets
    differ by at most ``tolerance_s``. Pairs are taken nearest-onset first
    and each note is used at most once on either side. Notes without a
    match get ``bends=None``. Returns ``notes``.
    """
    candidates = []
    for i, note in enumerate(notes):
        for j, other in enumerate(bend_notes):
            gap = abs(note.start_s - other.start_s)
            if note.pitch_midi == other.pitch_midi and gap <= tolerance_s + 1e-9:
                candidates.append((gap, i, j))
    candidates.sort()
    used_notes: set[int] = set()
    used_bends: set[int] = set()
    for note in notes:
        note.bends = None
    for _, i, j in candidates:
        if i in used_notes or j in used_bends:
            continue
        used_notes.add(i)
        used_bends.add(j)
        source = bend_notes[j].bends
        notes[i].bends = list(source) if source is not None else None
    return list(notes)


def _to_notes(raw: Sequence[RawRileyNote]) -> list[Note]:
    notes = [
        Note(
            pitch_midi=int(pitch),
            start_s=float(onset),
            end_s=float(offset),
            velocity=float(velocity),
            confidence=float(velocity),
        )
        for onset, offset, pitch, velocity in raw
        if offset > onset
    ]
    notes.sort(key=lambda n: (n.start_s, n.pitch_midi))
    return notes


def transcribe(
    input_path: str | Path,
    instrument: str = "guitar",
    on_progress: ProgressCallback = null_progress,
    cache: StageCache | None = None,
    predictor: Predictor | None = None,
    bend_transcribe: BendTranscribeFn | None = None,
    device: str | None = None,
) -> tuple[TranscriptionResult, bool]:
    """Hybrid transcription of a guitar stem: Riley notes, Basic Pitch bends.

    Returns ``(result, cache_hit)`` like :func:`basic_pitch.transcribe`. The
    merged result is cached under stage ``transcription`` and
    :func:`transcription_version`; ``bend_transcribe`` (default:
    :func:`basic_pitch.transcribe`, resolved at call time) keeps its own
    cache entry. ``predictor`` (default: the pinned model on ``device``) and
    ``bend_transcribe`` are injectable for tests.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise TranscriptionError(f"input audio not found: {input_path}")
    if instrument not in INSTRUMENTS:
        raise TranscriptionError(
            f"the Riley model only transcribes {', '.join(INSTRUMENTS)}, "
            f"not {instrument!r}"
        )
    if cache is None:
        cache = StageCache(input_path)

    version = transcription_version(instrument)
    cached = cache.get(STAGE, version)
    if cached is not None:
        on_progress(STAGE, 100.0)
        return (
            TranscriptionResult(note_events=NoteEvents.from_dict(cached["note_events"])),
            True,
        )

    on_progress(STAGE, 0.0)
    if predictor is None:
        def predictor(path: Path) -> list[RawRileyNote]:
            return predict(path, device=device)

    notes = _to_notes(predictor(input_path))
    on_progress(STAGE, 50.0)
    if bend_transcribe is None:
        bend_transcribe = basic_pitch.transcribe
    bend_result, _ = bend_transcribe(input_path, instrument=instrument, cache=cache)
    merge_bends(notes, bend_result.note_events.notes)
    result = TranscriptionResult(
        note_events=NoteEvents(
            notes=notes, instrument=instrument, model_version=MODEL_VERSION
        )
    )
    cache.put(STAGE, version, {"note_events": result.note_events.to_dict()})
    on_progress(STAGE, 100.0)
    return result, False
