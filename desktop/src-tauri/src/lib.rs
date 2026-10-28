//! tabgen Studio: a thin shell that runs `python -m tabgen.worker`.
//!
//! The UI holds no musical logic. Each job spawns one worker process, writes
//! the request line to its stdin and forwards every NDJSON line of its stdout
//! to the frontend through a channel (protocol: `tabgen/worker/__init__.py`).

use std::io::{BufRead, BufReader, Read, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};

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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![default_python, run_worker])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
