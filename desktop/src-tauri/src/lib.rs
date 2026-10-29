//! tabgen Studio: a thin shell that runs `python -m tabgen.worker`.
//!
//! The UI holds no musical logic. Each job spawns one worker process, writes
//! the request line to its stdin and forwards every NDJSON line of its stdout
//! to the frontend through a channel (protocol: `tabgen/worker/__init__.py`).

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use serde::Serialize;
use tauri::ipc::Channel;
use tauri::{Manager, State};

/// Lines of worker stderr kept for error reporting.
const STDERR_TAIL_LINES: usize = 20;

/// Grace period between SIGTERM and SIGKILL when a job is cancelled.
const CANCEL_GRACE: Duration = Duration::from_secs(2);

/// A running job: the worker's pid (also its process group id) and whether
/// the UI asked to cancel it.
struct Job {
    pid: u32,
    cancelled: bool,
}

/// Running jobs by the id the frontend gave to `run_worker`.
#[derive(Default, Clone)]
struct Jobs(Arc<Mutex<HashMap<String, Job>>>);

impl Jobs {
    fn lock(&self) -> std::sync::MutexGuard<'_, HashMap<String, Job>> {
        self.0
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
    }
}

/// Send `signal` to the whole process group led by `pid` (the worker and
/// anything it started: ffmpeg, torch/dataloader processes).
fn signal_group(pid: u32, signal: i32) {
    if let Ok(pgid) = libc::pid_t::try_from(pid) {
        // SAFETY: killpg only takes plain integers; an unknown group is ESRCH.
        unsafe {
            libc::killpg(pgid, signal);
        }
    }
}

/// Watch over the group led by `pid` from outside this process: a tiny `sh`
/// blocks reading a pipe we hold, so when the UI process dies without
/// reaching the exit handler (crash, SIGKILL, dev-mode reload) the pipe hits
/// EOF and the reaper sends SIGTERM then SIGKILL to the whole group.
fn spawn_reaper(pid: u32) -> Option<std::process::Child> {
    let script = format!(
        "read -r _ || {{ kill -s TERM -- -{pid} 2>/dev/null; sleep 2; kill -s KILL -- -{pid} 2>/dev/null; }}"
    );
    Command::new("sh")
        .args(["-c", &script])
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .ok()
}

/// Stand the reaper down once its job ended (the group id may be reused):
/// a line on its stdin makes `read` succeed, so it exits without killing.
fn release_reaper(reaper: Option<std::process::Child>) {
    if let Some(mut reaper) = reaper {
        if let Some(stdin) = reaper.stdin.as_mut() {
            let _ = stdin.write_all(b"done\n");
        }
        drop(reaper.stdin.take());
        let _ = reaper.wait();
    }
}

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
    /// True when the job ended because `cancel_worker` was called for it.
    cancelled: bool,
}

/// Run one worker job: `request` is the JSON request object; each stdout
/// line is sent on `on_line` as it arrives. Fails only when the process
/// cannot be started (e.g. a wrong interpreter path). With a `job_id` the
/// job can be stopped by `cancel_worker`; the worker runs in its own process
/// group so cancelling also stops the processes it started.
#[tauri::command]
async fn run_worker(
    jobs: State<'_, Jobs>,
    python: String,
    request: serde_json::Value,
    job_id: Option<String>,
    on_line: Channel<String>,
) -> Result<WorkerExit, String> {
    let jobs = jobs.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let mut child = Command::new(&python)
            .args(["-m", "tabgen.worker"])
            .current_dir(repo_root())
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .process_group(0)
            .spawn()
            .map_err(|err| format!("cannot start Python at '{python}': {err}"))?;
        let reaper = spawn_reaper(child.id());
        if let Some(id) = &job_id {
            jobs.lock().insert(
                id.clone(),
                Job {
                    pid: child.id(),
                    cancelled: false,
                },
            );
        }
        let result = drive_worker(&mut child, &request, &on_line);
        if result.is_err() {
            // a failed pipe must not leave the worker running unobserved
            signal_group(child.id(), libc::SIGKILL);
            let _ = child.wait();
        }
        release_reaper(reaper);
        let cancelled = job_id
            .and_then(|id| jobs.lock().remove(&id))
            .is_some_and(|job| job.cancelled);
        result.map(|(code, stderr_tail)| WorkerExit {
            code,
            stderr_tail,
            cancelled,
        })
    })
    .await
    .map_err(|err| err.to_string())?
}

/// Write the request, forward stdout lines and wait for the exit; returns
/// the exit code (-1 when killed by a signal) and the stderr tail.
fn drive_worker(
    child: &mut std::process::Child,
    request: &serde_json::Value,
    on_line: &Channel<String>,
) -> Result<(i32, String), String> {
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
    Ok((status.code().unwrap_or(-1), tail))
}

/// Stop a job started with `job_id`: SIGTERM to the worker's process group,
/// SIGKILL after a short grace period. Returns false when no such job is
/// running (already finished).
#[tauri::command]
fn cancel_worker(jobs: State<'_, Jobs>, job_id: String) -> bool {
    let pid = {
        let mut map = jobs.lock();
        let Some(job) = map.get_mut(&job_id) else {
            return false;
        };
        job.cancelled = true;
        job.pid
    };
    signal_group(pid, libc::SIGTERM);
    let jobs = jobs.inner().clone();
    std::thread::spawn(move || {
        std::thread::sleep(CANCEL_GRACE);
        // run_worker drops the job only after stdout hit EOF and the
        // worker was reaped; until then some process of the group still
        // holds the pipe, so the group id cannot have been reused
        let leader_alive = jobs.lock().get(&job_id).is_some_and(|job| job.pid == pid);
        if leader_alive {
            signal_group(pid, libc::SIGKILL);
        }
    });
    true
}

/// Stop every running job on app exit: SIGTERM each process group, wait the
/// cancel grace period, then SIGKILL whatever is left (an already-gone group
/// is just ESRCH). Blocks on purpose: a background thread like the one in
/// `cancel_worker` would die with the exiting process before the SIGKILL.
fn kill_all_jobs(jobs: &Jobs) {
    let pids: Vec<u32> = jobs.lock().values().map(|job| job.pid).collect();
    if pids.is_empty() {
        return;
    }
    for &pid in &pids {
        signal_group(pid, libc::SIGTERM);
    }
    std::thread::sleep(CANCEL_GRACE);
    for &pid in &pids {
        signal_group(pid, libc::SIGKILL);
    }
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

/// Show a result artifact's folder in the file manager: the directory
/// itself, or the parent of a file, handed to `xdg-open` (the desktop's
/// default handler for directories). Returns the directory opened.
#[tauri::command]
fn open_folder(path: String) -> Result<String, String> {
    let path = Path::new(&path);
    let dir = if path.is_dir() {
        path
    } else {
        path.parent()
            .filter(|dir| dir.is_dir())
            .ok_or_else(|| format!("folder not found: {}", path.display()))?
    };
    let mut child = Command::new("xdg-open")
        .arg(dir)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|err| format!("cannot run xdg-open: {err}"))?;
    // reap it in the background: xdg-open may wait for the file manager
    std::thread::spawn(move || {
        let _ = child.wait();
    });
    Ok(dir.to_string_lossy().into_owned())
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
        .manage(Jobs::default())
        .invoke_handler(tauri::generate_handler![
            default_python,
            run_worker,
            cancel_worker,
            file_exists,
            probe_audio,
            open_folder,
            startup_open
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            // closing the last window also raises ExitRequested, so this one
            // event covers both window close and explicit exit
            if matches!(event, tauri::RunEvent::ExitRequested { .. }) {
                kill_all_jobs(&app.state::<Jobs>());
            }
        });
}
