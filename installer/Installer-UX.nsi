; Copyright(C) 2024-2025 Advanced Micro Devices, Inc. All rights reserved.
; SPDX-License-Identifier: MIT
; GAIA Installer UX Script - Additional tasks for the main installer

; This file contains additional UX-related functions that can be included
; by the main Installer.nsi script.

; Include required plugins and macros
!include LogicLib.nsh

; Include modern UI elements
!include "MUI2.nsh"

; Define constants - moved to the top so they're available throughout the script
!define PRODUCT_NAME "AMD AI UX"
!define GITHUB_REPO "https://github.com/aigdat/open-webui.git"
!define EMPTY_FILE_NAME "empty_file.txt"
!define ICON_FILE "..\static\gaia.ico"

; This is a compile-time fix to make sure that our selfhost CI runner can successfully install,
; since LOCALAPPDATA points to C:\Windows for "system users"
!ifdef CI
  !if ${CI} == "ON"
    InstallDir "C:\Users\jfowe\AppData\Local\GAIA"
  !else
    InstallDir "$LOCALAPPDATA\GAIA"
  !endif
!else
  InstallDir "$LOCALAPPDATA\GAIA"
!endif

; Read version from version.py
!tempfile TMPFILE
!system 'python -c "with open(\"../version.py\") as f: exec(f.read()); print(version_with_hash)" > "${TMPFILE}"'
!define /file GAIA_VERSION "${TMPFILE}"
!delfile "${TMPFILE}"

; Define variables
Var GAIA_STRING
Var AMD_AI_UX_CONDA_ENV
Var PythonVersion
Var LogFilePath

; Finish Page settings
!define MUI_TEXT_FINISH_INFO_TITLE "GAIA installed successfully!"
!define MUI_TEXT_FINISH_INFO_TEXT "$GAIA_STRING has been installed successfully! A shortcut has been added to your Desktop. What would you like to do next?"

!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION RunAmdOpenWebUI
!define MUI_FINISHPAGE_RUN_TEXT "Run AMD AI UX"
!define MUI_FINISHPAGE_RUN_NOTCHECKED

;!define MUI_FINISHPAGE_SHOWREADME
;!define MUI_FINISHPAGE_SHOWREADME_FUNCTION RunAmdOpenWebUI
;!define MUI_FINISHPAGE_SHOWREADME_TEXT "Run $PRODUCT_NAME"
;!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

; MUI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

; Set the installer icon
Icon ${ICON_FILE}

; Language settings
LangString MUI_TEXT_WELCOME_INFO_TITLE "${LANG_ENGLISH}" "Welcome to the $GAIA_STRING Installer"
LangString MUI_TEXT_WELCOME_INFO_TEXT "${LANG_ENGLISH}" "This wizard will install $GAIA_STRING on your computer."
LangString MUI_TEXT_DIRECTORY_TITLE "${LANG_ENGLISH}" "Select Installation Directory"
LangString MUI_TEXT_INSTALLING_TITLE "${LANG_ENGLISH}" "Installing $GAIA_STRING"
LangString MUI_TEXT_FINISH_TITLE "${LANG_ENGLISH}" "Installation Complete"
LangString MUI_TEXT_FINISH_SUBTITLE "${LANG_ENGLISH}" "Thank you for installing GAIA!"
LangString MUI_TEXT_ABORT_TITLE "${LANG_ENGLISH}" "Installation Aborted"
LangString MUI_TEXT_ABORT_SUBTITLE "${LANG_ENGLISH}" "Installation has been aborted."
LangString MUI_BUTTONTEXT_FINISH "${LANG_ENGLISH}" "Finish"
LangString MUI_TEXT_LICENSE_TITLE ${LANG_ENGLISH} "License Agreement"
LangString MUI_TEXT_LICENSE_SUBTITLE ${LANG_ENGLISH} "Please review the license terms before installing GAIA."

Function .onInit
  ; Initialize variables
  StrCpy $GAIA_STRING "${PRODUCT_NAME}"
  StrCpy $AMD_AI_UX_CONDA_ENV "amd_ai_ux"
  StrCpy $PythonVersion "3.11"
  ; Fix the log file path to avoid variable substitution issues
  StrCpy $LogFilePath "$INSTDIR\amd_ai_ux_install.log"
FunctionEnd

; Define a section for the installation
Section "Install Main Components" SEC01
  ; Remove FileOpen/FileWrite for log file, replace with DetailPrint
  DetailPrint "*** INSTALLATION STARTED ***"
  DetailPrint "------------------------"
  DetailPrint "- Installation Section -"
  DetailPrint "------------------------"

  ; Check if directory exists before proceeding
  IfFileExists "$INSTDIR\*.*" 0 continue_install
    ${IfNot} ${Silent}
      MessageBox MB_YESNO "An existing GAIA installation was found at $INSTDIR.$\n$\nWould you like to remove it and continue with the installation?" IDYES remove_dir
      ; If user selects No, show exit message and quit the installer
      MessageBox MB_OK "Installation cancelled. Exiting installer..."
      DetailPrint "Installation cancelled by user"
      Quit
    ${Else}
      GoTo remove_dir
    ${EndIf}

  remove_dir:
    ; Attempt conda remove of the env, to help speed things up
    ExecWait 'conda env remove -yp "$INSTDIR\$AMD_AI_UX_CONDA_ENV"'
    ; Try to remove directory and verify it was successful
    RMDir /r "$INSTDIR"
    DetailPrint "- Deleted all contents of install dir"

    IfFileExists "$INSTDIR\*.*" 0 continue_install
      ${IfNot} ${Silent}
        MessageBox MB_OK "Unable to remove existing installation. Please close any applications using GAIA and try again."
      ${EndIf}
      DetailPrint "Failed to remove existing installation"
      Quit

  continue_install:
    ; Create fresh directory
    CreateDirectory "$INSTDIR"

    ; Set the output path for future operations
    SetOutPath "$INSTDIR"

    DetailPrint "Starting '$GAIA_STRING' Installation..."
    DetailPrint 'Configuration:'
    DetailPrint '  Install Dir: $INSTDIR'
    DetailPrint '-------------------------------------------'

    ; Pack GAIA into the installer
    ; Exclude hidden files (like .git, .gitignore) and the installation folder itself
    ; TODO: necessary for OpenWebUI? => File /r /x installer /x .* /x ..\*.pyc ..\*.* gaia_ux_installer.py
    ;DetailPrint "- Packaged $GAIA_STRING repo"

    ; Check if conda is available
    ExecWait 'where conda' $2
    DetailPrint "- Checked if conda is available"

    ; If conda is not found, show a message and exit
    ; Otherwise, continue with the installation
    StrCmp $2 "0" create_env conda_not_available

    conda_not_available:
      DetailPrint "- Conda not installed."
      ${IfNot} ${Silent}
        MessageBox MB_YESNO "Conda is not installed. Would you like to install Miniconda?" IDYES install_miniconda IDNO exit_installer
      ${Else}
        GoTo install_miniconda
      ${EndIf}

    exit_installer:
      DetailPrint "- Something went wrong. Exiting installer"
      Quit

    install_miniconda:
      DetailPrint "-------------"
      DetailPrint "- Miniconda -"
      DetailPrint "-------------"
      DetailPrint "- Downloading Miniconda installer..."
      ExecWait 'curl -s -o "$TEMP\Miniconda3-latest-Windows-x86_64.exe" "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"'

      ; Install Miniconda silently
      ExecWait '"$TEMP\Miniconda3-latest-Windows-x86_64.exe" /InstallationType=JustMe /AddToPath=1 /RegisterPython=0 /S /D=$PROFILE\miniconda3' $2
      ; Check if Miniconda installation was successful
      ${If} $2 == 0
        DetailPrint "- Miniconda installation successful"
        ${IfNot} ${Silent}
          MessageBox MB_OK "Miniconda has been successfully installed."
        ${EndIf}

        StrCpy $R1 "$PROFILE\miniconda3\Scripts\conda.exe"
        GoTo create_env

      ${Else}
        DetailPrint "- Miniconda installation failed"
        ${IfNot} ${Silent}
          MessageBox MB_OK "Error: Miniconda installation failed. Installation will be aborted."
        ${EndIf}
        GoTo exit_installer
      ${EndIf}

    create_env:
      DetailPrint "---------------------"
      DetailPrint "- Conda Environment -"
      DetailPrint "---------------------"

      DetailPrint "- Initializing conda..."
      ; Use the appropriate conda executable
      ${If} $R1 == ""
        StrCpy $R1 "conda"
      ${EndIf}
      ; Initialize conda (needed for systems where conda was previously installed but not initialized)
      nsExec::ExecToLog '"$R1" init'

      DetailPrint "- Creating a Python $PythonVersion environment named 'gaia_env' in the installation directory: $INSTDIR..."
      ExecWait '"$R1" create -p "$INSTDIR\$AMD_AI_UX_CONDA_ENV" python=$PythonVersion -y' $R0

      ; Check if the environment creation was successful (exit code should be 0)
      StrCmp $R0 0 install_app env_creation_failed

    env_creation_failed:
      DetailPrint "- ERROR: Environment creation failed"
      ; Display an error message and exit
      ${IfNot} ${Silent}
        MessageBox MB_OK "ERROR: Failed to create the Python environment. Installation will be aborted."
      ${EndIf}
      Quit

    install_app:

      DetailPrint "---------------------"
      DetailPrint "- AMD AI UX Installation -"
      DetailPrint "---------------------"

      DetailPrint "- Starting AMD AI UX installation (this can take 5-10 minutes)..."
      DetailPrint "- See $LogFilePath for detailed progress..."
      ; Call the batch file with required parameters
      ; Execute the Python script
      DetailPrint "- Executing Python script to handle the installation..."
      DetailPrint "- Command: $INSTDIR\gaia_env\python.exe gaia_ux_installer.py --install-dir $INSTDIR"
      
      ; Execute the Python script with the installation directory as a named parameter
      ExecWait '"$INSTDIR\gaia_env\python.exe" gaia_ux_installer.py --install-dir "$INSTDIR"' $0
      
      DetailPrint "- Python script return code: $0"
      
      ; Check if the installation was successful
      ${If} $0 == "0"
        DetailPrint "- Open WebUI installation completed successfully"
      ${Else}
        DetailPrint "- ERROR: Open WebUI installation failed with return code: $0"
        DetailPrint "- Please check the log file for details: $LogFilePath"
      ${EndIf}
      
      DetailPrint "- Open WebUI installation process completed"

    Return
  
SectionEnd


Function RunAmdOpenWebUI
  ExecShell "open" "$DESKTOP\AMD-AI-UX.lnk"
FunctionEnd
