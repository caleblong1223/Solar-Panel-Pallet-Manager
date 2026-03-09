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

  let spawn_result = Command::new(python)
    .arg("-m")
    .arg("uvicorn")
    .arg("app.main:app")
    .arg("--host")
    .arg("127.0.0.1")
    .arg("--port")
    .arg("8000")
    .current_dir(&backend_dir)
    .spawn();

  if let Err(err) = spawn_result {
    eprintln!("Failed to start bundled backend: {err}");
  }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
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
