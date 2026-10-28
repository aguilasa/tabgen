//! tabgen Studio: a thin shell that runs `python -m tabgen.worker`.
//!
//! The UI holds no musical logic. Each job spawns one worker process, writes
//! the request line to its stdin and forwards every NDJSON line of its stdout
//! to the frontend through a channel (protocol: `tabgen/worker/__init__.py`).

use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};

use serde::Serialize;
use tauri::ipc::Channel;

/// Lines of worker stderr kept for error reporting.
const STDERR_TAIL_LINES: usize = 20;

/// Repository root: the worker runs from there so `tabgen` is importable.
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."))
}

/// Default interpreter: the repository's `.venv` (v1 uses the existing install).
#[tauri::command]
fn default_python() -> String {
    repo_root()
        .join(".venv/bin/python")
        .to_string_lossy()
        .into_owned()
}

#[derive(Serialize)]
struct WorkerExit {
    /// Process exit code (-1 when killed by a signal).
    code: i32,
    /// Last lines the worker wrote to stderr.
    stderr_tail: String,
}

/// Run one worker job: `request` is the JSON request object; each stdout
/// line is sent on `on_line` as it arrives. Fails only when the process
/// cannot be started (e.g. a wrong interpreter path).
#[tauri::command]
async fn run_worker(
    python: String,
    request: serde_json::Value,
    on_line: Channel<String>,
) -> Result<WorkerExit, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let mut child = Command::new(&python)
            .args(["-m", "tabgen.worker"])
            .current_dir(repo_root())
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|err| format!("cannot start Python at '{python}': {err}"))?;

        let mut stdin = child.stdin.take().expect("stdin is piped");
        writeln!(stdin, "{request}").map_err(|err| err.to_string())?;
        drop(stdin);

        let mut stderr = child.stderr.take().expect("stderr is piped");
        let stderr_reader = std::thread::spawn(move || {
            let mut text = String::new();
            let _ = stderr.read_to_string(&mut text);
            text
        });

        let stdout = child.stdout.take().expect("stdout is piped");
        for line in BufReader::new(stdout).lines() {
            let line = line.map_err(|err| err.to_string())?;
            if !line.trim().is_empty() {
                let _ = on_line.send(line);
            }
        }

        let status = child.wait().map_err(|err| err.to_string())?;
        let stderr_text = stderr_reader.join().unwrap_or_default();
        let lines: Vec<&str> = stderr_text.lines().collect();
        let tail = lines[lines.len().saturating_sub(STDERR_TAIL_LINES)..].join("\n");
        Ok(WorkerExit {
            code: status.code().unwrap_or(-1),
            stderr_tail: tail,
        })
    })
    .await
    .map_err(|err| err.to_string())?
}

/// Whether a path still points to a regular file (recents drop the others).
#[tauri::command]
fn file_exists(path: String) -> bool {
    Path::new(&path).is_file()
}

#[derive(Serialize)]
struct AudioInfo {
    /// Duration in seconds, from the container.
    duration_s: f64,
    /// ffprobe container name (e.g. `mp3`, `wav`, `flac`).
    format: String,
    /// Sample rate of the first audio stream, when known.
    sample_rate: Option<u32>,
    /// Channels of the first audio stream, when known.
    channels: Option<u32>,
}

/// Read duration and format of an audio file with `ffprobe` (ffmpeg is
/// already a tabgen requirement). Fails when the file is missing or is not
/// decodable audio.
#[tauri::command]
async fn probe_audio(path: String) -> Result<AudioInfo, String> {
    tauri::async_runtime::spawn_blocking(move || {
        if !Path::new(&path).is_file() {
            return Err(format!("file not found: {path}"));
        }
        let output = Command::new("ffprobe")
            .args([
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "format=duration,format_name:stream=sample_rate,channels",
                "-of",
                "json",
            ])
            .arg(&path)
            .output()
            .map_err(|err| format!("cannot run ffprobe: {err}"))?;
        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("ffprobe failed: {}", stderr.trim()));
        }
        let json: serde_json::Value =
            serde_json::from_slice(&output.stdout).map_err(|err| err.to_string())?;
        let stream = &json["streams"][0];
        if stream.is_null() {
            return Err("no audio stream".into());
        }
        let duration_s = json["format"]["duration"]
            .as_str()
            .and_then(|d| d.parse::<f64>().ok())
            .ok_or("unknown duration")?;
        let as_u32 = |v: &serde_json::Value| {
            v.as_u64()
                .or_else(|| v.as_str().and_then(|s| s.parse().ok()))
                .and_then(|n| u32::try_from(n).ok())
        };
        Ok(AudioInfo {
            duration_s,
            format: json["format"]["format_name"]
                .as_str()
                .unwrap_or_default()
                .to_string(),
            sample_rate: as_u32(&stream["sample_rate"]),
            channels: as_u32(&stream["channels"]),
        })
    })
    .await
    .map_err(|err| err.to_string())?
}

static STARTUP_OPEN_TAKEN: AtomicBool = AtomicBool::new(false);

/// Dev-only: a file named by `TABGEN_OPEN` is opened once at startup through
/// the same path as the file picker (lets a headless run exercise it).
/// Release builds ignore the variable.
#[tauri::command]
fn startup_open() -> Option<String> {
    if !cfg!(debug_assertions) || STARTUP_OPEN_TAKEN.swap(true, Ordering::SeqCst) {
        return None;
    }
    std::env::var("TABGEN_OPEN").ok().filter(|p| !p.is_empty())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            default_python,
            run_worker,
            file_exists,
            probe_audio,
            startup_open
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
