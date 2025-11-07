use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

// ========== Application State ==========

pub struct AppState {
    ollama_process: Mutex<Option<Child>>,
    backend_process: Mutex<Option<Child>>,
}

impl AppState {
    fn new() -> Self {
        Self {
            ollama_process: Mutex::new(None),
            backend_process: Mutex::new(None),
        }
    }
}

// ========== Utility Functions ==========

/// Get the app data directory path
fn get_app_data_dir() -> Result<PathBuf, String> {
    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            Ok(home.join("Library").join("Application Support").join("open-webui"))
        } else {
            Err("Could not determine home directory".to_string())
        }
    }
    #[cfg(target_os = "windows")]
    {
        if let Some(appdata) = std::env::var_os("APPDATA") {
            Ok(PathBuf::from(appdata).join("open-webui"))
        } else {
            Err("Could not determine AppData directory".to_string())
        }
    }
    #[cfg(target_os = "linux")]
    {
        if let Some(home) = dirs::home_dir() {
            Ok(home.join(".local").join("share").join("open-webui"))
        } else {
            Err("Could not determine home directory".to_string())
        }
    }
}

/// Get the Python venv directory path
fn get_venv_dir() -> Result<PathBuf, String> {
    Ok(get_app_data_dir()?.join("venv"))
}

/// Get the Python executable path from venv
fn get_python_executable() -> Result<PathBuf, String> {
    let venv_dir = get_venv_dir()?;
    #[cfg(target_os = "windows")]
    {
        Ok(venv_dir.join("Scripts").join("python.exe"))
    }
    #[cfg(not(target_os = "windows"))]
    {
        Ok(venv_dir.join("bin").join("python"))
    }
}

/// Get the pip executable path from venv
fn get_pip_executable() -> Result<PathBuf, String> {
    let venv_dir = get_venv_dir()?;
    #[cfg(target_os = "windows")]
    {
        Ok(venv_dir.join("Scripts").join("pip.exe"))
    }
    #[cfg(not(target_os = "windows"))]
    {
        Ok(venv_dir.join("bin").join("pip"))
    }
}

// ========== Python Environment Commands ==========

#[tauri::command]
async fn check_bundled_python() -> Result<bool, String> {
    // For Phase 3, we'll check if system Python 3.12 is available
    // In Phase 6, this will check for bundled Python in resources
    let output = Command::new("python3.12")
        .arg("--version")
        .output();
    
    match output {
        Ok(output) => {
            let version_str = String::from_utf8_lossy(&output.stdout);
            Ok(version_str.contains("Python 3.12"))
        }
        Err(_) => {
            // Try just "python3" as fallback
            let output = Command::new("python3")
                .arg("--version")
                .output();
            
            match output {
                Ok(output) => {
                    let version_str = String::from_utf8_lossy(&output.stdout);
                    Ok(version_str.contains("Python 3.12"))
                }
                Err(_) => Ok(false),
            }
        }
    }
}

#[tauri::command]
async fn initialize_python_environment() -> Result<(), String> {
    let venv_dir = get_venv_dir()?;
    
    // Create app data directory if it doesn't exist
    let app_data_dir = get_app_data_dir()?;
    std::fs::create_dir_all(&app_data_dir)
        .map_err(|e| format!("Failed to create app data directory: {}", e))?;
    
    // Skip if venv already exists
    if venv_dir.exists() {
        return Ok(());
    }
    
    // Try python3.12 first, then python3
    let python_cmd = if Command::new("python3.12").arg("--version").output().is_ok() {
        "python3.12"
    } else {
        "python3"
    };
    
    // Create venv
    let output = Command::new(python_cmd)
        .arg("-m")
        .arg("venv")
        .arg(&venv_dir)
        .output()
        .map_err(|e| format!("Failed to create venv: {}", e))?;
    
    if !output.status.success() {
        return Err(format!(
            "Failed to create Python virtual environment: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    
    Ok(())
}

#[tauri::command]
async fn check_python_dependencies() -> Result<bool, String> {
    let python_exe = get_python_executable()?;
    
    if !python_exe.exists() {
        return Ok(false);
    }
    
    // Check if key dependencies are installed
    let test_imports = "import fastapi, uvicorn, chromadb";
    let output = Command::new(&python_exe)
        .arg("-c")
        .arg(test_imports)
        .output()
        .map_err(|e| format!("Failed to check dependencies: {}", e))?;
    
    Ok(output.status.success())
}

#[tauri::command]
async fn install_python_dependencies(app_handle: tauri::AppHandle) -> Result<(), String> {
    let pip_exe = get_pip_executable()?;
    
    // Get the backend requirements.txt path
    let resource_path = app_handle
        .path()
        .resource_dir()
        .map_err(|e| format!("Failed to get resource directory: {}", e))?;
    
    let requirements_path = resource_path
        .join("backend")
        .join("requirements.txt");
    
    if !requirements_path.exists() {
        return Err("requirements.txt not found".to_string());
    }
    
    // Install dependencies
    let output = Command::new(&pip_exe)
        .arg("install")
        .arg("-r")
        .arg(&requirements_path)
        .arg("--no-cache-dir")
        .output()
        .map_err(|e| format!("Failed to install dependencies: {}", e))?;
    
    if !output.status.success() {
        return Err(format!(
            "Failed to install Python dependencies: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    
    Ok(())
}

// ========== Ollama Commands ==========

#[tauri::command]
async fn check_ollama_installed() -> Result<bool, String> {
    #[cfg(target_os = "macos")]
    let ollama_paths = vec![
        "/usr/local/bin/ollama",
        "/opt/homebrew/bin/ollama",
    ];
    
    #[cfg(target_os = "linux")]
    let ollama_paths = vec![
        "/usr/local/bin/ollama",
        "/usr/bin/ollama",
    ];
    
    #[cfg(target_os = "windows")]
    let ollama_paths = vec![
        "C:\\Program Files\\Ollama\\ollama.exe",
    ];
    
    for path in ollama_paths {
        if std::path::Path::new(path).exists() {
            return Ok(true);
        }
    }
    
    // Also check if ollama is in PATH
    let output = Command::new("ollama")
        .arg("--version")
        .output();
    
    Ok(output.is_ok())
}

#[tauri::command]
async fn install_ollama() -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        // Download and run Ollama installer for macOS
        let output = Command::new("curl")
            .arg("-fsSL")
            .arg("https://ollama.ai/install.sh")
            .stdout(Stdio::piped())
            .spawn()
            .and_then(|child| {
                Command::new("sh")
                    .stdin(child.stdout.unwrap())
                    .output()
            })
            .map_err(|e| format!("Failed to install Ollama: {}", e))?;
        
        if !output.status.success() {
            return Err(format!(
                "Ollama installation failed: {}",
                String::from_utf8_lossy(&output.stderr)
            ));
        }
    }
    
    #[cfg(target_os = "linux")]
    {
        // Run install script for Linux
        let output = Command::new("sh")
            .arg("-c")
            .arg("curl -fsSL https://ollama.ai/install.sh | sh")
            .output()
            .map_err(|e| format!("Failed to install Ollama: {}", e))?;
        
        if !output.status.success() {
            return Err(format!(
                "Ollama installation failed: {}",
                String::from_utf8_lossy(&output.stderr)
            ));
        }
    }
    
    #[cfg(target_os = "windows")]
    {
        return Err("Please download and install Ollama manually from https://ollama.ai".to_string());
    }
    
    Ok(())
}

#[tauri::command]
async fn check_ollama_running() -> Result<bool, String> {
    let client = reqwest::Client::new();
    
    match client
        .get("http://127.0.0.1:11434/api/tags")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

#[tauri::command]
async fn start_ollama(state: tauri::State<'_, AppState>) -> Result<(), String> {
    // Check if already running
    if check_ollama_running().await? {
        return Ok(());
    }
    
    // Start Ollama serve
    let child = Command::new("ollama")
        .arg("serve")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("Failed to start Ollama: {}", e))?;
    
    // Store process handle (drop the lock before await)
    {
        let mut ollama_process = state.ollama_process.lock().unwrap();
        *ollama_process = Some(child);
    }
    
    // Wait a moment for Ollama to start
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
    
    Ok(())
}

// ========== Backend Server Commands ==========

#[tauri::command]
async fn start_backend_server(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let python_exe = get_python_executable()?;
    
    // Get backend directory
    let resource_path = app_handle
        .path()
        .resource_dir()
        .map_err(|e| format!("Failed to get resource directory: {}", e))?;
    
    let backend_dir = resource_path.join("backend");
    
    if !backend_dir.exists() {
        return Err("Backend directory not found".to_string());
    }
    
    // Start the backend server
    let child = Command::new(&python_exe)
        .arg("-m")
        .arg("uvicorn")
        .arg("open_webui.main:app")
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg("8080")
        .current_dir(&backend_dir)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("Failed to start backend server: {}", e))?;
    
    // Store process handle
    {
        let mut backend_process = state.backend_process.lock().unwrap();
        *backend_process = Some(child);
    }
    
    Ok(())
}

#[tauri::command]
async fn check_backend_health() -> Result<bool, String> {
    let client = reqwest::Client::new();
    
    match client
        .get("http://127.0.0.1:8080/health")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
    {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => {
            // Try root endpoint as fallback
            match client
                .get("http://127.0.0.1:8080/")
                .timeout(std::time::Duration::from_secs(2))
                .send()
                .await
            {
                Ok(response) => Ok(response.status().is_success()),
                Err(_) => Ok(false),
            }
        }
    }
}

// ========== Utility Commands ==========

#[tauri::command]
async fn get_app_data_path() -> Result<String, String> {
    Ok(get_app_data_dir()?
        .to_str()
        .ok_or("Invalid path")?  
        .to_string())
}

// ========== Main Application Entry Point ==========

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .plugin(tauri_plugin_http::init())
    .manage(AppState::new())
    .invoke_handler(tauri::generate_handler![
      check_bundled_python,
      initialize_python_environment,
      check_python_dependencies,
      install_python_dependencies,
      check_ollama_installed,
      install_ollama,
      check_ollama_running,
      start_ollama,
      start_backend_server,
      check_backend_health,
      get_app_data_path,
    ])
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
