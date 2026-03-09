use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

use tauri::Manager;

fn backend_is_running() -> bool {
  let addr = "127.0.0.1:8000";
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
    backend_dir.join(".venv").join("bin").join("python3"),
    backend_dir.join(".venv").join("bin").join("python"),
  ];
  candidates
    .into_iter()
    .find(|path| path.is_file())
}

fn start_bundled_backend(app: &tauri::App) {
  if backend_is_running() {
    return;
  }

  let resource_dir = match app.path().resource_dir() {
    Ok(path) => path,
    Err(err) => {
      eprintln!("Failed to resolve resource dir: {err}");
      return;
    }
  };
  let backend_dir = match resolve_backend_dir(&resource_dir) {
    Some(path) => path,
    None => {
      eprintln!("Bundled backend directory not found under {}", resource_dir.display());
      return;
    }
  };
  let python = match resolve_python_executable(&backend_dir) {
    Some(path) => path,
    None => {
      eprintln!("Bundled python executable not found in {}", backend_dir.display());
      return;
    }
  };

  let app_data_dir = match app.path().app_data_dir() {
    Ok(path) => path,
    Err(err) => {
      eprintln!("Failed to resolve app data dir: {err}");
      return;
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

  let spawn_result = Command::new(python)
    .arg("-m")
    .arg("uvicorn")
    .arg("app.main:app")
    .arg("--host")
    .arg("127.0.0.1")
    .arg("--port")
    .arg("8000")
    .env("DATABASE_URL", database_url)
    .env("LOCAL_IMPORT_ROOT", import_root.as_os_str())
    .env("LOCAL_EXPORT_ROOT", export_root.as_os_str())
    .current_dir(&backend_dir)
    .spawn();

  if let Err(err) = spawn_result {
    eprintln!("Failed to start bundled backend: {err}");
  }
}

#[tauri::command]
fn open_with_system(target: String) -> Result<(), String> {
  if target.trim().is_empty() {
    return Err("Target cannot be empty".to_string());
  }

  #[cfg(target_os = "macos")]
  let mut command = {
    let mut cmd = Command::new("open");
    cmd.arg(&target);
    cmd
  };

  #[cfg(target_os = "windows")]
  let mut command = {
    let mut cmd = Command::new("cmd");
    cmd.arg("/C").arg("start").arg("").arg(&target);
    cmd
  };

  #[cfg(all(unix, not(target_os = "macos")))]
  let mut command = {
    let mut cmd = Command::new("xdg-open");
    cmd.arg(&target);
    cmd
  };

  command
    .spawn()
    .map_err(|err| format!("Failed to open with system default app: {err}"))?;
  Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
      if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
      }
    }))
    .invoke_handler(tauri::generate_handler![open_with_system])
    .setup(|app| {
      start_bundled_backend(app);
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
