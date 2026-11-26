#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{Manager, RunEvent, WindowEvent};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// The spawned Stella Python backend (sidecar or `python main.py`), killed on exit.
enum BackendChild {
    Sidecar(CommandChild),
    Process(std::process::Child),
}

impl BackendChild {
    fn kill(self) {
        match self {
            BackendChild::Sidecar(c) => {
                let _ = c.kill(); // CommandChild::kill consumes self
            }
            BackendChild::Process(mut c) => {
                let _ = c.kill();
            }
        }
    }
}

struct Backend(Mutex<Option<BackendChild>>);

fn repo_root() -> std::path::PathBuf {
    // CARGO_MANIFEST_DIR = <repo>/frontend/src-tauri
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .unwrap()
        .to_path_buf()
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let mut started = false;

            // 1. Packaged app: launch the bundled sidecar "stella-backend"
            match app.shell().sidecar("stella-backend") {
                Ok(sidecar) => match sidecar.spawn() {
                    Ok((_rx, child)) => {
                        println!("[stella] backend sidecar started (pid {})", child.pid());
                        app.manage(Backend(Mutex::new(Some(BackendChild::Sidecar(child)))));
                        started = true;
                    }
                    Err(e) => eprintln!("[stella] sidecar spawn failed: {e}"),
                },
                Err(e) => eprintln!("[stella] no sidecar available: {e}"),
            }

            // 2. Dev fallback: `python main.py` from the repo root.
            if !started {
                match std::process::Command::new("python")
                    .arg("main.py")
                    .current_dir(repo_root())
                    .spawn()
                {
                    Ok(child) => {
                        println!("[stella] backend started via `python main.py`");
                        app.manage(Backend(Mutex::new(Some(BackendChild::Process(child)))));
                    }
                    Err(e) => eprintln!("[stella] could not start backend: {e}"),
                }
            }

            // 3. Companion overlay window: transparent, always-on-top, frameless.
            //    Loads the /companion route which hosts StellaCompanion.
            let companion = tauri::WebviewWindowBuilder::new(app, "companion", "/companion")
                .title("Stella Companion")
                .transparent(true)
                .always_on_top(true)
                .decorations(false)
                .inner_size(400.0, 400.0)
                .min_inner_size(200.0, 200.0)
                .focused(false)
                .build()
                .map_err(|e| eprintln!("[stella] companion window failed: {e}"))
                .ok();

            if let Some(win) = companion {
                // Position at bottom-right by default; position is managed by frontend localStorage.
                let _ = win.set_position(tauri::PhysicalPosition::new(20, 20));
                #[cfg(debug_assertions)]
                let _ = win.open_devtools();
            }

            #[cfg(debug_assertions)]
            {
                let window = app.get_window("main").unwrap();
                window.open_devtools();
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building stella desktop app")
        .run(|app, event| {
            if let RunEvent::ExitRequested { .. } = event {
                if let Some(b) = app.try_state::<Backend>() {
                    if let Some(child) = b.0.lock().unwrap().take() {
                        child.kill();
                    }
                }
            }
            if let RunEvent::WindowEvent { label, event: WindowEvent::CloseRequested { api, .. }, .. } = &event {
                if label == "main" {
                    let _ = api;
                }
            }
        });
}
