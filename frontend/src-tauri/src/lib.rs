use std::env;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_handle = match BackendProcessHandle::spawn() {
        Ok(handle) => handle,
        Err(err) => {
            log::error!("failed to start local backend: {err}");
            BackendProcessHandle::empty()
        }
    };

    tauri::Builder::default()
        .manage(backend_handle)
        .setup(|app| {
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

#[derive(Clone)]
struct BackendProcessHandle(Arc<Mutex<Option<Child>>>);

impl BackendProcessHandle {
    fn with_child(child: Child) -> Self {
        BackendProcessHandle(Arc::new(Mutex::new(Some(child))))
    }

    fn empty() -> Self {
        BackendProcessHandle(Arc::new(Mutex::new(None)))
    }

    fn spawn() -> std::io::Result<Self> {
        let python = env::var("TAURI_BACKEND_PYTHON").unwrap_or_else(|_| "python3".into());
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let repo_root = manifest_dir
            .parent()
            .and_then(|p| p.parent())
            .expect("project root missing");
        let backend_dir = repo_root.join("backend");

        if !backend_dir.exists() {
            return Err(std::io::Error::new(
                std::io::ErrorKind::NotFound,
                format!("backend directory not found at {backend_dir:?}"),
            ));
        }

        let mut command = Command::new(python);
        command
            .arg("-m")
            .arg("uvicorn")
            .arg("app.main:app")
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg("8000")
            .current_dir(&backend_dir)
            .env("PYTHONUNBUFFERED", "1")
            .stdout(Stdio::null())
            .stderr(Stdio::null());

        command.spawn().map(BackendProcessHandle::with_child)
    }
}

impl Drop for BackendProcessHandle {
    fn drop(&mut self) {
        if let Some(mut child) = self.0.lock().unwrap().take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}
