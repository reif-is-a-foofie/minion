// Minion desktop shell.
//
// Responsibilities:
// - Resolve (and create) the user's Minion data dir + inbox
// - Spawn the Python API sidecar as a managed child process (dev: use repo venv;
//   prod: use a bundled sidecar binary -- see scripts/build_sidecar.sh)
// - Expose minimal Tauri commands the frontend uses:
//     app_config, copy_into_inbox, reveal_in_finder
// Native OS file drops are delivered to the frontend by Tauri v2 as the
// `tauri://drag-drop` event; the frontend forwards the paths to
// `copy_into_inbox`.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{Manager, WindowEvent};

struct AppState {
    sidecar: Mutex<Option<Child>>,
    data_dir: PathBuf,
    inbox: PathBuf,
    api_port: u16,
}

// ---------------------------------------------------------------------------
// Path resolution
// ---------------------------------------------------------------------------

fn resolve_data_dir() -> PathBuf {
    if let Ok(p) = std::env::var("MINION_DATA_DIR") {
        return PathBuf::from(p);
    }
    if let Some(base) = dirs::data_dir() {
        return base.join("Minion").join("data");
    }
    PathBuf::from(".minion/data")
}

fn resolve_inbox(data_dir: &Path) -> PathBuf {
    if let Ok(p) = std::env::var("MINION_INBOX") {
        return PathBuf::from(p);
    }
    data_dir.join("inbox")
}

// ---------------------------------------------------------------------------
// Sidecar
// ---------------------------------------------------------------------------

fn find_dev_python_sidecar() -> Option<(PathBuf, Vec<String>)> {
    // <repo>/desktop/src-tauri/  -> <repo>/chatgpt_mcp_memory/src/api.py
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let repo = manifest.parent()?.parent()?;
    let api = repo.join("chatgpt_mcp_memory").join("src").join("api.py");
    if !api.exists() {
        return None;
    }
    let venv = repo.join("chatgpt_mcp_memory").join(".venv").join("bin").join("python");
    let python = if venv.exists() { venv } else { PathBuf::from("python3") };
    Some((python, vec![api.to_string_lossy().into_owned()]))
}

fn spawn_sidecar(data_dir: &Path, api_port: u16) -> Option<Child> {
    let (python, mut args) = find_dev_python_sidecar()?;
    args.push("--port".into());
    args.push(api_port.to_string());

    let mut cmd = Command::new(python);
    cmd.args(&args)
        .env("MINION_DATA_DIR", data_dir)
        .env("MINION_API_PORT", api_port.to_string())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());

    match cmd.spawn() {
        Ok(child) => Some(child),
        Err(e) => {
            eprintln!("[minion] failed to spawn sidecar: {e}");
            None
        }
    }
}

// ---------------------------------------------------------------------------
// Tauri commands
// ---------------------------------------------------------------------------

#[tauri::command]
fn app_config(state: tauri::State<AppState>) -> serde_json::Value {
    serde_json::json!({
        "data_dir": state.data_dir.to_string_lossy(),
        "inbox": state.inbox.to_string_lossy(),
        "api_port": state.api_port,
        "api_base": format!("http://127.0.0.1:{}", state.api_port),
    })
}

#[tauri::command]
fn copy_into_inbox(state: tauri::State<AppState>, paths: Vec<String>) -> Result<Vec<String>, String> {
    let inbox = &state.inbox;
    fs::create_dir_all(inbox).map_err(|e| e.to_string())?;

    let mut moved = Vec::new();
    for src in paths {
        let src_path = PathBuf::from(&src);
        if !src_path.exists() || !src_path.is_file() {
            continue;
        }
        let mut dest = inbox.join(
            src_path
                .file_name()
                .map(|s| s.to_os_string())
                .unwrap_or_else(|| "unnamed".into()),
        );
        if dest.exists() {
            let stem = src_path
                .file_stem()
                .map(|s| s.to_string_lossy().into_owned())
                .unwrap_or_else(|| "file".into());
            let ext = src_path
                .extension()
                .map(|s| format!(".{}", s.to_string_lossy()))
                .unwrap_or_default();
            let mut n = 1;
            loop {
                let candidate = inbox.join(format!("{stem} ({n}){ext}"));
                if !candidate.exists() {
                    dest = candidate;
                    break;
                }
                n += 1;
            }
        }
        fs::copy(&src_path, &dest).map_err(|e| e.to_string())?;
        moved.push(dest.to_string_lossy().into_owned());
    }
    Ok(moved)
}

#[tauri::command]
fn reveal_in_finder(path: String) -> Result<(), String> {
    let p = PathBuf::from(&path);
    let target = if p.is_file() {
        p.parent().map(Path::to_path_buf).unwrap_or(p)
    } else {
        p
    };
    #[cfg(target_os = "macos")]
    {
        Command::new("open").arg(target).spawn().map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "windows")]
    {
        Command::new("explorer").arg(target).spawn().map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open").arg(target).spawn().map_err(|e| e.to_string())?;
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let data_dir = resolve_data_dir();
    let inbox = resolve_inbox(&data_dir);
    let _ = fs::create_dir_all(&data_dir);
    let _ = fs::create_dir_all(&inbox);
    let api_port: u16 = std::env::var("MINION_API_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8765);

    let child = spawn_sidecar(&data_dir, api_port);
    let state = AppState {
        sidecar: Mutex::new(child),
        data_dir: data_dir.clone(),
        inbox: inbox.clone(),
        api_port,
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            app_config,
            copy_into_inbox,
            reveal_in_finder
        ])
        .on_window_event(|window, event| {
            if matches!(event, WindowEvent::Destroyed) {
                if let Some(state) = window.app_handle().try_state::<AppState>() {
                    if let Ok(mut guard) = state.sidecar.lock() {
                        if let Some(mut child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running minion desktop");
}
