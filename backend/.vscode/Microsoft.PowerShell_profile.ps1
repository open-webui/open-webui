# filepath: c:\\Users\\te-yihsu\\OneDrive - Advanced Micro Devices Inc\\Documents\\WindowsPowerShell\\Microsoft.PowerShell_profile.ps1
function prompt {
  if ($env:VIRTUAL_ENV) {
    $venvName = Split-Path $env:VIRTUAL_ENV -Leaf
    Write-Host "($venvName) " -NoNewline -ForegroundColor Green # Display venv name in Green
  }
  "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) " # Return the rest of the prompt
} # This closes the prompt function

# Aliases and Functions
Remove-Item Alias:set -Force -ErrorAction SilentlyContinue # Remove built-in 'set' alias
function set {
    Get-ChildItem Env:
}