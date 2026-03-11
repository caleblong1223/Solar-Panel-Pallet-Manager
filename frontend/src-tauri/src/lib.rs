use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::thread;
use std::time::Duration;
use std::{fs, io};

use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};
use tauri::Manager;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
struct DesktopPrefs {
  show_backend_terminal: bool,
}

impl Default for DesktopPrefs {
  fn default() -> Self {
    Self {
      show_backend_terminal: false,
    }
  }
}

fn desktop_prefs_path<R: tauri::Runtime, M: tauri::Manager<R>>(manager: &M) -> Option<PathBuf> {
  let app_data_dir = manager.path().app_data_dir().ok()?;
  Some(app_data_dir.join("desktop_prefs.json"))
}

fn save_desktop_prefs<R: tauri::Runtime, M: tauri::Manager<R>>(manager: &M, prefs: &DesktopPrefs) -> Result<(), String> {
  let prefs_path = desktop_prefs_path(manager).ok_or("Unable to resolve app data directory".to_string())?;
  if let Some(parent) = prefs_path.parent() {
    fs::create_dir_all(parent).map_err(|err| format!("Unable to create preferences directory: {err}"))?;
  }
  let content = serde_json::to_string_pretty(prefs).map_err(|err| format!("Unable to serialize preferences: {err}"))?;
  fs::write(&prefs_path, content).map_err(|err| format!("Unable to write preferences: {err}"))?;
  Ok(())
}

fn load_desktop_prefs<R: tauri::Runtime, M: tauri::Manager<R>>(manager: &M) -> DesktopPrefs {
  let Some(prefs_path) = desktop_prefs_path(manager) else {
    return DesktopPrefs::default();
  };

  match fs::read_to_string(&prefs_path) {
    Ok(content) => {
      let trimmed = content.trim();
      if trimmed.is_empty() {
        let defaults = DesktopPrefs::default();
        let _ = save_desktop_prefs(manager, &defaults);
        return defaults;
      }
      match serde_json::from_str::<DesktopPrefs>(trimmed) {
        Ok(prefs) => prefs,
        Err(err) => {
          eprintln!("Failed to parse desktop prefs from {}: {err}", prefs_path.display());
          let defaults = DesktopPrefs::default();
          let _ = save_desktop_prefs(manager, &defaults);
          defaults
        }
      }
    }
    Err(err) if err.kind() == io::ErrorKind::NotFound => DesktopPrefs::default(),
    Err(err) => {
      eprintln!("Failed to read desktop prefs from {}: {err}", prefs_path.display());
      DesktopPrefs::default()
    }
  }
}

fn backend_is_running() -> bool {
  let addr = "127.0.0.1:8010";
  match addr.parse() {
    Ok(socket_addr) => TcpStream::connect_timeout(&socket_addr, Duration::from_millis(250)).is_ok(),
    Err(_) => false,
  }
}

fn resolve_backend_dir(resource_dir: &Path) -> Option<PathBuf> {
  let candidates = [
    resource_dir.join("backend"),
    resource_dir.join("_up_").join("_up_").join("backend"),
  ];
  candidates.into_iter().find(|path| path.is_dir())
}

fn resolve_python_executable(backend_dir: &Path) -> Option<PathBuf> {
  let candidates = [
    backend_dir.join(".venv").join("Scripts").join("python.exe"),
    backend_dir.join(".venv").join("Scripts").join("python"),
    backend_dir.join(".venv").join("bin").join("python3"),
    backend_dir.join(".venv").join("bin").join("python"),
  ];
  candidates.into_iter().find(|path| path.is_file())
}

fn start_bundled_backend(app: &tauri::AppHandle) -> Result<(), String> {
  if backend_is_running() {
    return Ok(());
  }

  let resource_dir = match app.path().resource_dir() {
    Ok(path) => path,
    Err(err) => {
      return Err(format!("Failed to resolve resource dir: {err}"));
    }
  };
  let backend_dir = match resolve_backend_dir(&resource_dir) {
    Some(path) => path,
    None => {
      return Err(format!(
        "Bundled backend directory not found under {}",
        resource_dir.display()
      ));
    }
  };
  let python = match resolve_python_executable(&backend_dir) {
    Some(path) => path,
    None => {
      return Err(format!(
        "Bundled python executable not found in {}",
        backend_dir.display()
      ));
    }
  };

  let app_data_dir = match app.path().app_data_dir() {
    Ok(path) => path,
    Err(err) => {
      return Err(format!("Failed to resolve app data dir: {err}"));
    }
  };
  let import_root = app_data_dir.join("IMPORTED DATA").join("LOCAL_IMPORTS");
  let export_root = app_data_dir.join("EXPORTS").join("LOCAL_EXPORTS");
  if let Err(err) = std::fs::create_dir_all(&import_root) {
    eprintln!("Failed to create import directory {}: {err}", import_root.display());
  }
  if let Err(err) = std::fs::create_dir_all(&export_root) {
    eprintln!("Failed to create export directory {}: {err}", export_root.display());
  }
  let database_url = format!("sqlite+pysqlite:///{}", app_data_dir.join("pallet_manager.db").display());
  let prefs = load_desktop_prefs(app);

  let mut command = Command::new(python);
  command
    .arg("scripts/run_local_backend.py")
    .arg("--host")
    .arg("127.0.0.1")
    .arg("--port")
    .arg("8010")
    .arg("--database-url")
    .arg(database_url)
    .env("LOCAL_IMPORT_ROOT", import_root.as_os_str())
    .env("LOCAL_EXPORT_ROOT", export_root.as_os_str())
    .current_dir(&backend_dir);

  #[cfg(target_os = "windows")]
  if !prefs.show_backend_terminal {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x08000000;
    command.creation_flags(CREATE_NO_WINDOW);
  }

  let spawn_result = command.spawn();

  if let Err(err) = spawn_result {
    return Err(format!("Failed to start bundled backend: {err}"));
  }
  Ok(())
}

fn legacy_local_export_roots(app: &tauri::AppHandle) -> Vec<PathBuf> {
  let mut roots: Vec<PathBuf> = Vec::new();

  if let Ok(app_data_dir) = app.path().app_data_dir() {
    roots.push(app_data_dir.join("EXPORTS").join("LOCAL_EXPORTS"));
  }

  if let Ok(resource_dir) = app.path().resource_dir() {
    roots.push(resource_dir.join("data").join("EXPORTS").join("LOCAL_EXPORTS"));
    roots.push(
      resource_dir
        .join("_up_")
        .join("_up_")
        .join("data")
        .join("EXPORTS")
        .join("LOCAL_EXPORTS"),
    );
  }

  if let Ok(exe_path) = std::env::current_exe() {
    if let Some(exe_dir) = exe_path.parent() {
      roots.push(exe_dir.join("data").join("EXPORTS").join("LOCAL_EXPORTS"));
      roots.push(
        exe_dir
          .join("_up_")
          .join("_up_")
          .join("data")
          .join("EXPORTS")
          .join("LOCAL_EXPORTS"),
      );
    }
  }

  roots.sort();
  roots.dedup();
  roots
}

fn normalize_open_target(app: &tauri::AppHandle, target: &str) -> String {
  let trimmed = target.trim();
  if trimmed.is_empty() {
    return trimmed.to_string();
  }

  #[cfg(target_os = "windows")]
  {
    let lower = trimmed.to_ascii_lowercase();
    if lower.starts_with("http://") || lower.starts_with("https://") {
      return trimmed.to_string();
    }

    let decoded = if lower.starts_with("file:///") {
      trimmed
        .trim_start_matches("file:///")
        .replace("%20", " ")
        .replace('/', "\\")
    } else {
      trimmed.replace("%20", " ")
    };

    let decoded_lower = decoded.to_ascii_lowercase();
    let legacy_prefixes = [
      "\\data\\exports\\local_exports\\",
      "data\\exports\\local_exports\\",
      "/data/exports/local_exports/",
      "data/exports/local_exports/",
    ];

    for prefix in legacy_prefixes {
      if decoded_lower.starts_with(prefix) {
        let suffix = decoded[prefix.len()..].trim_start_matches(['\\', '/']);
        for root in legacy_local_export_roots(app) {
          let candidate = root.join(suffix);
          if candidate.exists() {
            return candidate.to_string_lossy().into_owned();
          }
        }
        if let Some(root) = legacy_local_export_roots(app).into_iter().next() {
          return root.join(suffix).to_string_lossy().into_owned();
        }
        return decoded;
      }
    }

    if decoded.len() >= 3 {
      let bytes = decoded.as_bytes();
      let has_drive = bytes[1] == b':' && (bytes[2] == b'\\' || bytes[2] == b'/');
      if has_drive {
        return decoded;
      }
    }

    return decoded;
  }

  #[cfg(not(target_os = "windows"))]
  {
    trimmed.to_string()
  }
}

fn open_path_with_system(normalized_target: &str) -> Result<(), String> {
  #[cfg(target_os = "macos")]
  let mut command = {
    let mut cmd = Command::new("open");
    cmd.arg(normalized_target);
    cmd
  };

  #[cfg(target_os = "windows")]
  let mut command = {
    let mut cmd = Command::new("cmd");
    cmd.arg("/C").arg("start").arg("").arg(normalized_target);
    cmd
  };

  #[cfg(all(unix, not(target_os = "macos")))]
  let mut command = {
    let mut cmd = Command::new("xdg-open");
    cmd.arg(normalized_target);
    cmd
  };

  command
    .spawn()
    .map_err(|err| format!("Failed to open with system default app: {err}"))?;
  Ok(())
}

#[tauri::command]
fn open_with_system(app: tauri::AppHandle, target: String) -> Result<(), String> {
  if target.trim().is_empty() {
    return Err("Target cannot be empty".to_string());
  }

  let normalized_target = normalize_open_target(&app, &target);
  open_path_with_system(&normalized_target)
}

#[tauri::command]
fn download_and_open_with_system(
  app: tauri::AppHandle,
  url: String,
  bearer_token: Option<String>,
  file_name: Option<String>,
) -> Result<(), String> {
  if url.trim().is_empty() {
    return Err("URL cannot be empty".to_string());
  }

  let client = Client::builder()
    .build()
    .map_err(|err| format!("Failed to create HTTP client: {err}"))?;
  let mut request = client.get(url.trim());
  if let Some(token) = bearer_token.as_deref() {
    if !token.trim().is_empty() {
      request = request.bearer_auth(token.trim());
    }
  }
  let response = request
    .send()
    .map_err(|err| format!("Failed to download file: {err}"))?;
  if !response.status().is_success() {
    let status = response.status();
    let body = response.text().unwrap_or_default();
    return Err(format!("Download failed ({status}): {body}"));
  }

  let download_dir = app
    .path()
    .app_data_dir()
    .map_err(|err| format!("Unable to resolve app data directory: {err}"))?
    .join("OPENED_FILES");
  fs::create_dir_all(&download_dir)
    .map_err(|err| format!("Unable to create opened files directory: {err}"))?;

  let requested_name = file_name
    .as_deref()
    .map(str::trim)
    .filter(|value| !value.is_empty())
    .unwrap_or("download.bin");
  let sanitized_name = Path::new(requested_name)
    .file_name()
    .and_then(|value| value.to_str())
    .filter(|value| !value.trim().is_empty())
    .unwrap_or("download.bin");
  let target_path = download_dir.join(sanitized_name);
  let bytes = response
    .bytes()
    .map_err(|err| format!("Failed to read download bytes: {err}"))?;
  fs::write(&target_path, &bytes).map_err(|err| format!("Failed to write temp file: {err}"))?;
  open_path_with_system(&target_path.to_string_lossy())
}

#[tauri::command]
fn open_backend_terminal() -> Result<(), String> {
  #[cfg(target_os = "windows")]
  {
    Command::new("conhost.exe")
      .args(["cmd.exe", "/K", "echo Pallet Manager backend terminal"])
      .spawn()
      .map_err(|error| format!("Unable to open backend terminal: {error}"))?;
    return Ok(());
  }

  #[cfg(target_os = "macos")]
  {
    Command::new("open")
      .args(["-a", "Terminal"])
      .spawn()
      .map_err(|error| format!("Unable to open backend terminal: {error}"))?;
    return Ok(());
  }

  #[cfg(all(unix, not(target_os = "macos")))]
  {
    Command::new("x-terminal-emulator")
      .spawn()
      .or_else(|_| Command::new("gnome-terminal").spawn())
      .or_else(|_| Command::new("konsole").spawn())
      .or_else(|_| Command::new("xterm").spawn())
      .map_err(|error| format!("Unable to open backend terminal: {error}"))?;
    return Ok(());
  }
}

#[tauri::command]
fn get_backend_terminal_setting(app: tauri::AppHandle) -> bool {
  load_desktop_prefs(&app).show_backend_terminal
}

#[tauri::command]
fn set_backend_terminal_setting(app: tauri::AppHandle, show_backend_terminal: bool) -> Result<(), String> {
  let prefs = DesktopPrefs {
    show_backend_terminal,
  };
  save_desktop_prefs(&app, &prefs)
}

#[tauri::command]
fn ensure_local_backend(app: tauri::AppHandle) -> Result<bool, String> {
  if backend_is_running() {
    return Ok(true);
  }

  start_bundled_backend(&app)?;

  for _ in 0..40 {
    if backend_is_running() {
      return Ok(true);
    }
    thread::sleep(Duration::from_millis(250));
  }
  Ok(false)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
      if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_fullscreen(false);
        let _ = window.maximize();
        let _ = window.set_focus();
      }
    }))
    .invoke_handler(tauri::generate_handler![
      open_with_system,
      download_and_open_with_system,
      open_backend_terminal,
      get_backend_terminal_setting,
      set_backend_terminal_setting,
      ensure_local_backend
    ])
    .setup(|app| {
      if let Some(window) = app.get_webview_window("main") {
        let _ = window.set_fullscreen(false);
        let _ = window.maximize();
      }
      if let Err(err) = start_bundled_backend(&app.handle()) {
        eprintln!("{err}");
      }
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
