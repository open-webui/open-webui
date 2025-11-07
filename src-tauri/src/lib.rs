use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;
use serde::{Deserialize, Serialize};

// ========== Application State ==========

pub struct AppState {
    ollama_process: Mutex<Option<Child>>,
    backend_process: Mutex<Option<Child>>,
    preferences: Mutex<AppPreferences>,
    ollama_started_by_us: Mutex<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppPreferences {
    pub auto_start_ollama: bool,
    pub keep_ollama_running_on_exit: bool,
    pub backend_port: u16,
}

impl Default for AppPreferences {
    fn default() -> Self {
        Self {
            auto_start_ollama: true,
            keep_ollama_running_on_exit: true,
            backend_port: 8080,
        }
    }
}

impl AppState {
    fn new() -> Self {
        Self {
            ollama_process: Mutex::new(None),
            backend_process: Mutex::new(None),
            preferences: Mutex::new(AppPreferences::default()),
            ollama_started_by_us: Mutex::new(false),
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

/// Get the preferences file path
fn get_preferences_path() -> Result<PathBuf, String> {
    Ok(get_app_data_dir()?.join("preferences.json"))
}

/// Load preferences from file
fn load_preferences() -> Result<AppPreferences, String> {
    let prefs_path = get_preferences_path()?;
    
    if !prefs_path.exists() {
        return Ok(AppPreferences::default());
    }
    
    let contents = std::fs::read_to_string(&prefs_path)
        .map_err(|e| format!("Failed to read preferences: {}", e))?;
    
    serde_json::from_str(&contents)
        .map_err(|e| format!("Failed to parse preferences: {}", e))
}

/// Save preferences to file
fn save_preferences(prefs: &AppPreferences) -> Result<(), String> {
    let prefs_path = get_preferences_path()?;
    
    // Ensure directory exists
    if let Some(parent) = prefs_path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create preferences directory: {}", e))?;
    }
    
    let contents = serde_json::to_string_pretty(prefs)
        .map_err(|e| format!("Failed to serialize preferences: {}", e))?;
    
    std::fs::write(&prefs_path, contents)
        .map_err(|e| format!("Failed to write preferences: {}", e))?;
    
    Ok(())
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
    let was_already_running = check_ollama_running().await?;
    
    if was_already_running {
        // Mark that we didn't start it
        let mut started = state.ollama_started_by_us.lock().unwrap();
        *started = false;
        return Ok(());
    }
    
    // Start Ollama serve
    let child = Command::new("ollama")
        .arg("serve")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("Failed to start Ollama: {}", e))?;
    
    // Store process handle and mark that we started it
    {
        let mut ollama_process = state.ollama_process.lock().unwrap();
        *ollama_process = Some(child);
        
        let mut started = state.ollama_started_by_us.lock().unwrap();
        *started = true;
    }
    
    // Wait a moment for Ollama to start
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
    
    Ok(())
}

#[tauri::command]
async fn check_ollama_model(model_name: String) -> Result<bool, String> {
    let client = reqwest::Client::new();
    
    match client
        .get("http://127.0.0.1:11434/api/tags")
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
    {
        Ok(response) => {
            if !response.status().is_success() {
                return Ok(false);
            }
            
            match response.json::<serde_json::Value>().await {
                Ok(data) => {
                    // Check if the model exists in the list
                    if let Some(models) = data.get("models").and_then(|m| m.as_array()) {
                        for model in models {
                            if let Some(name) = model.get("name").and_then(|n| n.as_str()) {
                                // Model names might include tags like "llama3:8b" or just "llama3"
                                if name.starts_with(&model_name) {
                                    return Ok(true);
                                }
                            }
                        }
                    }
                    Ok(false)
                }
                Err(e) => Err(format!("Failed to parse Ollama response: {}", e)),
            }
        }
        Err(e) => Err(format!("Failed to check Ollama models: {}", e)),
    }
}

#[tauri::command]
async fn pull_ollama_model(model_name: String) -> Result<(), String> {
    // Use ollama pull command
    let output = Command::new("ollama")
        .arg("pull")
        .arg(&model_name)
        .output()
        .map_err(|e| format!("Failed to pull model: {}", e))?;
    
    if !output.status.success() {
        return Err(format!(
            "Failed to pull Ollama model {}: {}",
            model_name,
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    
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

// ========== Preferences Commands ==========

#[tauri::command]
async fn get_preferences(state: tauri::State<'_, AppState>) -> Result<AppPreferences, String> {
    let prefs = state.preferences.lock().unwrap();
    Ok(prefs.clone())
}

#[tauri::command]
async fn update_preferences(
    state: tauri::State<'_, AppState>,
    preferences: AppPreferences,
) -> Result<(), String> {
    // Update state
    {
        let mut prefs = state.preferences.lock().unwrap();
        *prefs = preferences.clone();
    }
    
    // Save to file
    save_preferences(&preferences)?;
    
    Ok(())
}

// ========== Lifecycle Commands ==========

#[tauri::command]
async fn stop_backend_server(state: tauri::State<'_, AppState>) -> Result<(), String> {
    let mut backend_process = state.backend_process.lock().unwrap();
    
    if let Some(mut child) = backend_process.take() {
        child.kill()
            .map_err(|e| format!("Failed to stop backend server: {}", e))?;
    }
    
    Ok(())
}

#[tauri::command]
async fn stop_ollama(state: tauri::State<'_, AppState>) -> Result<(), String> {
    let mut ollama_process = state.ollama_process.lock().unwrap();
    
    if let Some(mut child) = ollama_process.take() {
        child.kill()
            .map_err(|e| format!("Failed to stop Ollama: {}", e))?;
    }
    
    Ok(())
}

#[tauri::command]
async fn restart_services(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    // Stop backend
    stop_backend_server(state.clone()).await?;
    
    // Wait a moment
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
    
    // Restart backend
    start_backend_server(app_handle, state).await?;
    
    Ok(())
}

#[tauri::command]
async fn get_service_status(state: tauri::State<'_, AppState>) -> Result<serde_json::Value, String> {
    let ollama_running = check_ollama_running().await.unwrap_or(false);
    let backend_running = check_backend_health().await.unwrap_or(false);
    
    let ollama_process_exists = {
        let process = state.ollama_process.lock().unwrap();
        process.is_some()
    };
    
    let backend_process_exists = {
        let process = state.backend_process.lock().unwrap();
        process.is_some()
    };
    
    Ok(serde_json::json!({
        "ollama": {
            "running": ollama_running,
            "process_managed": ollama_process_exists,
        },
        "backend": {
            "running": backend_running,
            "process_managed": backend_process_exists,
        }
    }))
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
      check_ollama_model,
      pull_ollama_model,
      start_backend_server,
      check_backend_health,
      get_preferences,
      update_preferences,
      stop_backend_server,
      stop_ollama,
      restart_services,
      get_service_status,
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
      
      // Load preferences
      let state = app.state::<AppState>();
      if let Ok(prefs) = load_preferences() {
        let mut state_prefs = state.preferences.lock().unwrap();
        *state_prefs = prefs;
      }
      
      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application")
    .run(|app_handle, event| {
      // Handle app exit
      if let tauri::RunEvent::ExitRequested { api, code: _, .. } = event {
        let state = app_handle.state::<AppState>();
        
        // Always stop backend server
        let mut backend_process = state.backend_process.lock().unwrap();
        if let Some(mut child) = backend_process.take() {
          let _ = child.kill();
        }
        drop(backend_process);
        
        // Stop Ollama only if we started it AND preference says to stop it
        let prefs = state.preferences.lock().unwrap();
        let started_by_us = state.ollama_started_by_us.lock().unwrap();
        
        if *started_by_us && !prefs.keep_ollama_running_on_exit {
          let mut ollama_process = state.ollama_process.lock().unwrap();
          if let Some(mut child) = ollama_process.take() {
            let _ = child.kill();
          }
        }
        
        // Allow exit
        api.prevent_exit();
      }
    });
}
