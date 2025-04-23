Goal: Modify RAUX launch scripts (`launch_raux.cmd`, `launch_raux.ps1`) to remove external miniconda dependencies and use self-contained, downloaded embedded Python distributions. We want to launch RAUX so that its using the installed "python" version in side the install_dir, rather than the global one. 


This plan includes examples from Lemonade installer in how they achieved this.

## RAUX Tasks (`gaia_raux_installer.py`, `launch_raux.*`, `Installer-UX.nsi`)

- [x] **Add Embedded Python 3.10 Setup:** In `Installer.nsi`, add logic to:
    - Create `$INSTDIR\python`.
    - Download Python embeddable zip (`${PYTHON_EMBED_URL}`) to `$INSTDIR\python\python.zip`.
    - Extract the zip to `$INSTDIR\python` (using `Expand-Archive`).
    - Delete the zip file.
    - Download `get-pip.py` (`${GET_PIP_URL}`) to `$INSTDIR\python`.
    - Run `$INSTDIR\python\python.exe $INSTDIR\python\get-pip.py` to install pip.
    - Delete `get-pip.py`.
    - Modify `$INSTDIR\python\python*._pth` to include `Lib` and `Lib\site-packages`.
- [ ] **Use Embedded Python for RAUX Installation:** In `gaia_raux_installer.py`:
    - Modify the `subprocess.run` call that executes the actual RAUX installation (likely another script like `install.py` within the RAUX package) to use the *RAUX-specific* embedded Python executable (`<raux_python_dir>/python.exe`).
    - Remove any Conda-related environment activation or path manipulation.
- [ ] **Update RAUX Launch Scripts:** Modify `launch_raux.cmd` and `launch_raux.ps1`:
    - Remove Conda activation logic.
    - Directly call the RAUX embedded Python executable (`%LOCALAPPDATA%\RAUX\python\python.exe` or PowerShell equivalent) to run the RAUX backend/frontend.
- [] **Add `bin` to User PATH:** Modify `Installer.nsi` (likely near the end of `SEC01`):
    - Use `ReadRegStr` to get the current user PATH from `HKCU\Environment`.
    - Check if `$INSTDIR\bin` is already in the PATH.
    - If `$INSTDIR\bin` is not found, use `setx PATH "$INSTDIR\bin;$CURRENT_PATH"` (without `-m`) to update the user PATH environment variable.

## Examples

### Lemonade Installer

```
; Lemonade Server Installer Script

!define /ifndef NPU_DRIVER_VERSION "32.0.203.237"

; Define main variables
Name "Lemonade Server"
OutFile "Lemonade_Server_Installer.exe"

; Include modern UI elements
!include "MUI2.nsh"

!include FileFunc.nsh

; Include LogicLib for logging in silent mode
!include LogicLib.nsh
Var LogHandle

Var LEMONADE_SERVER_STRING
Var HYBRID_SELECTED
Var HYBRID_CLI_OPTION

; Variables for CPU detection
Var cpuName
Var isCpuSupported
Var ryzenAiPos
Var seriesStartPos
Var currentChar

; Used for string manipulation
!include "StrFunc.nsh"
${StrLoc}

; Define a section for the installation
Section "Install Main Components" SEC01
SectionIn RO ; Read only, always installed
  DetailPrint "------------------------"
  DetailPrint "- Installation Section -"
  DetailPrint "------------------------"

  ; Once we're done downloading and installing the pip packages the size comes out to about 2GB
  AddSize 2097152

  ; Check if directory exists before proceeding
  IfFileExists "$INSTDIR\*.*" 0 continue_install
    ${IfNot} ${Silent}
      MessageBox MB_YESNO "An existing $LEMONADE_SERVER_STRING installation was found at $INSTDIR.$\n$\nWould you like to remove it and continue with the installation?" IDYES remove_dir
      ; If user selects No, show exit message and quit the installer
      MessageBox MB_OK "Installation cancelled. Exiting installer..."
      Quit
    ${Else}
      Goto remove_dir
    ${EndIf}

  remove_dir:
    ; Try to remove directory and verify it was successful
    
    ; Delete all remaining files
    RMDir /r "$INSTDIR"
    
    IfFileExists "$INSTDIR\*.*" 0 continue_install
      ${IfNot} ${Silent}
        MessageBox MB_OK "Unable to remove existing installation. Please close any applications using $LEMONADE_SERVER_STRING and try again."
      ${EndIf}
      Quit

  continue_install:
    ; Create fresh directory
    CreateDirectory "$INSTDIR"
    DetailPrint "*** INSTALLATION STARTED ***"

    ; Attach console to installation to enable logging
    System::Call 'kernel32::GetStdHandle(i -11)i.r0'
    StrCpy $LogHandle $0 ; Save the handle to LogHandle variable
    System::Call 'kernel32::AttachConsole(i -1)i.r1'
    ${If} $LogHandle = 0
      ${OrIf} $1 = 0
      System::Call 'kernel32::AllocConsole()'
      System::Call 'kernel32::GetStdHandle(i -11)i.r0'
      StrCpy $LogHandle $0 ; Update the LogHandle variable if the console was allocated
    ${EndIf}
    DetailPrint "- Initialized logging"

    ; Set the output path for future operations
    SetOutPath "$INSTDIR"

    DetailPrint "Starting '$LEMONADE_SERVER_STRING' Installation..."
    DetailPrint 'Configuration:'
    DetailPrint '  Install Dir: $INSTDIR'
    DetailPrint '  Minimum NPU Driver Version: ${NPU_DRIVER_VERSION}'
    DetailPrint '-------------------------------------------'

    # Pack turnkeyml repo into the installer
    # Exclude hidden files (like .git, .gitignore) and the installation folder itself
    File /r /x nsis.exe /x installer /x .* /x *.pyc /x docs /x examples /x utilities ..\*.* lemonade-server.bat

    # Create bin directory and move lemonade-server.bat there
    CreateDirectory "$INSTDIR\bin"
    Rename "$INSTDIR\lemonade-server.bat" "$INSTDIR\bin\lemonade-server.bat"

    DetailPrint "- Packaged repo"

    DetailPrint "Set up Python"
    CreateDirectory "$INSTDIR\python"
    ExecWait 'curl -s -o "$INSTDIR\python\python.zip" "https://www.python.org/ftp/python/3.10.9/python-3.10.9-embed-amd64.zip"'
    ExecWait 'tar -xf "$INSTDIR\python\python.zip" -C "$INSTDIR\python"'
    ExecWait 'curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py'
    ExecWait '$INSTDIR\python\python.exe get-pip.py --no-warn-script-location'
    
    FileOpen $2 "$INSTDIR\python\python310._pth" a
    FileSeek $2 0 END
    FileWrite $2 "$\r$\nLib$\r$\n"
    FileWrite $2 "$\r$\nLib\site-packages$\r$\n"
    FileClose $2

    DetailPrint "-------------------------"
    DetailPrint "- Lemonade Installation -"
    DetailPrint "-------------------------"


    DetailPrint "- Installing $LEMONADE_SERVER_STRING..."
    ${If} $HYBRID_SELECTED == "true"
      ExecWait '"$INSTDIR\python\python.exe" -m pip install "$INSTDIR"[llm-oga-hybrid] --no-warn-script-location' $8
    ${Else}
      ExecWait '"$INSTDIR\python\python.exe" -m pip install "$INSTDIR"[llm] --no-warn-script-location' $8
    ${EndIf}
    DetailPrint "- $LEMONADE_SERVER_STRING install return code: $8"

    ; Check if installation was successful (exit code should be 0)
    StrCmp $8 0 install_success install_failed

    install_success:
      DetailPrint "- $LEMONADE_SERVER_STRING installation successful"

      DetailPrint "*** INSTALLATION COMPLETED ***"
      # Create a shortcut inside $INSTDIR
      CreateShortcut "$INSTDIR\lemonade-server.lnk" "$INSTDIR\bin\lemonade-server.bat" "serve --keep-alive" "$INSTDIR\img\favicon.ico"

      ; Add bin folder to system PATH
      DetailPrint "- Adding bin directory to system PATH..."
      
      ; Get the current PATH value from the registry
      ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PATH"
      
      ; Add bin folder (containing 'lemonade-server') to path while avoiding duplicate entries
      ExecWait 'setx PATH "$INSTDIR\bin;$0" -m'
      
      DetailPrint "- Successfully updated system PATH"

      Goto end

    install_failed:
      DetailPrint "- $LEMONADE_SERVER_STRING installation failed"
      ${IfNot} ${Silent}
        MessageBox MB_OK "ERROR: $LEMONADE_SERVER_STRING package failed to install using pip. Installation will be aborted."
      ${EndIf}
      Quit

    end:
SectionEnd

Section "Install Ryzen AI Hybrid Execution" HybridSec
  DetailPrint "------------------------"
  DetailPrint "- Ryzen AI Section     -"
  DetailPrint "------------------------"

  ; Once we're done downloading and installing the archive the size comes out to about 370MB
  AddSize 388882

  nsExec::ExecToLog '$INSTDIR\python\Scripts\lemonade-install --ryzenai hybrid -y'

  Pop $R0  ; Return value
  DetailPrint "Hybrid execution mode install return code: $R0"

  ; Check if installation was successful (exit code should be 0)
  StrCmp $R0 0 end install_failed

  install_failed:
      DetailPrint "- Hybrid installation failed"
      ${IfNot} ${Silent}
        MessageBox MB_OK "ERROR: Hybrid mode failed to install using pip. Installation will be aborted."
      ${EndIf}
      Quit

  end:
SectionEnd

SubSection /e "Selected Models" ModelsSec
  Section /o "Qwen2.5-0.5B-Instruct-CPU" Qwen05Sec
    SectionIn 1
    AddSize 999604  ;
    StrCpy $9 "$9Qwen2.5-0.5B-Instruct-CPU "
  SectionEnd

  Section "Llama-3.2-1B-Instruct-Hybrid" Llama1BSec
    SectionIn 1
    AddSize 1884397  ;
    StrCpy $9 "$9Llama-3.2-1B-Instruct-Hybrid "
  SectionEnd

  Section "Llama-3.2-3B-Instruct-Hybrid" Llama3BSec
    SectionIn 1
    AddSize 4268402  ;
    StrCpy $9 "$9Llama-3.2-3B-Instruct-Hybrid "
  SectionEnd

  Section /o "Phi-3-Mini-Instruct-Hybrid" PhiSec
    SectionIn 1
    AddSize 4185551  ;
    StrCpy $9 "$9Phi-3-Mini-Instruct-Hybrid "
  SectionEnd

  Section /o "Qwen-1.5-7B-Chat-Hybrid" Qwen7BSec
    SectionIn 1
    AddSize 8835894  ;
    StrCpy $9 "$9Qwen-1.5-7B-Chat-Hybrid "
  SectionEnd

  Section /o "DeepSeek-R1-Distill-Llama-8B-Hybrid" DeepSeekLlama8BSec
    SectionIn 1
    AddSize 9084315  ;
    StrCpy $9 "$9DeepSeek-R1-Distill-Llama-8B-Hybrid "
  SectionEnd

  Section /o "DeepSeek-R1-Distill-Qwen-7B-Hybrid" DeepSeekQwen7BSec
    SectionIn 1
    AddSize 9502412  ;
    StrCpy $9 "$9DeepSeek-R1-Distill-Qwen-7B-Hybrid "
  SectionEnd

  Section "-Download Models" DownloadModels
    ${If} ${Silent}
        ${GetParameters} $CMDLINE
        ${GetOptions} $CMDLINE "/Models=" $R0
        ${If} $R0 != ""
            nsExec::ExecToLog '$INSTDIR\python\Scripts\lemonade-install --models $R0'
        ${Else}
            ; Otherwise, only the default CPU model will be installed
            nsExec::ExecToLog '$INSTDIR\python\Scripts\lemonade-install --models Qwen2.5-0.5B-Instruct-CPU'
        ${EndIf}
    ${Else}
        nsExec::ExecToLog '$INSTDIR\python\Scripts\lemonade-install --models $9'
    ${EndIf}
  SectionEnd

SubSectionEnd

Section "-Add Desktop Shortcut" ShortcutSec  
  CreateShortcut "$DESKTOP\lemonade-server.lnk" "$INSTDIR\bin\lemonade-server.bat" "serve --keep-alive" "$INSTDIR\img\favicon.ico"

SectionEnd

Function RunServer
  ExecShell "open" "$INSTDIR\LEMONADE-SERVER.lnk"
FunctionEnd

; Define constants for better readability
!define ICON_FILE "..\img\favicon.ico"

; Finish Page settings
!define MUI_TEXT_FINISH_INFO_TITLE "$LEMONADE_SERVER_STRING installed successfully!"
!define MUI_TEXT_FINISH_INFO_TEXT "A shortcut has been added to your Desktop. What would you like to do next?"

!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION RunServer
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_RUN_TEXT "Run Lemonade Server"

Function .onSelChange
    ; Check hybrid selection status
    StrCpy $HYBRID_SELECTED "false"
    SectionGetFlags ${HybridSec} $0
    IntOp $0 $0 & ${SF_SELECTED}
    StrCmp $0 ${SF_SELECTED} 0 hybrid_disabled
    StrCpy $HYBRID_SELECTED "true"
    
    ; If hybrid is enabled, check if at least one hybrid model is selected
    SectionGetFlags ${Llama1BSec} $1
    IntOp $1 $1 & ${SF_SELECTED}
    ${If} $1 == ${SF_SELECTED}
        Goto end
    ${EndIf}
    
    SectionGetFlags ${Llama3BSec} $1
    IntOp $1 $1 & ${SF_SELECTED}
    ${If} $1 == ${SF_SELECTED}
        Goto end
    ${EndIf}
    
    SectionGetFlags ${PhiSec} $1
    IntOp $1 $1 & ${SF_SELECTED}
    ${If} $1 == ${SF_SELECTED}
        Goto end
    ${EndIf}
    
    SectionGetFlags ${Qwen7BSec} $1
    IntOp $1 $1 & ${SF_SELECTED}
    ${If} $1 == ${SF_SELECTED}
        Goto end
    ${EndIf}
    
    SectionGetFlags ${DeepSeekLlama8BSec} $1
    IntOp $1 $1 & ${SF_SELECTED}
    ${If} $1 == ${SF_SELECTED}
        Goto end
    ${EndIf}
    
    SectionGetFlags ${DeepSeekQwen7BSec} $1
    IntOp $1 $1 & ${SF_SELECTED}
    ${If} $1 == ${SF_SELECTED}
        Goto end
    ${EndIf}
    
    ; If no hybrid model is selected, select Llama-1B by default
    SectionGetFlags ${Llama1BSec} $1
    IntOp $1 $1 | ${SF_SELECTED}
    SectionSetFlags ${Llama1BSec} $1
    MessageBox MB_OK "At least one hybrid model must be selected when hybrid execution is enabled. Llama-3.2-1B-Instruct-Hybrid has been automatically selected."
    Goto end
    
hybrid_disabled:
    ; When hybrid is disabled, select Qwen2.5-0.5B-Instruct-CPU and disable all other hybrid model selections
    SectionGetFlags ${Qwen05Sec} $1
    IntOp $1 $1 | ${SF_SELECTED}
    SectionSetFlags ${Qwen05Sec} $1

    SectionGetFlags ${Llama1BSec} $1
    IntOp $1 $1 & ${SECTION_OFF}
    SectionSetFlags ${Llama1BSec} $1
    
    SectionGetFlags ${Llama3BSec} $1
    IntOp $1 $1 & ${SECTION_OFF}
    SectionSetFlags ${Llama3BSec} $1
    
    SectionGetFlags ${PhiSec} $1
    IntOp $1 $1 & ${SECTION_OFF}
    SectionSetFlags ${PhiSec} $1
    
    SectionGetFlags ${Qwen7BSec} $1
    IntOp $1 $1 & ${SECTION_OFF}
    SectionSetFlags ${Qwen7BSec} $1
    
    SectionGetFlags ${DeepSeekLlama8BSec} $1
    IntOp $1 $1 & ${SECTION_OFF}
    SectionSetFlags ${DeepSeekLlama8BSec} $1
    
    SectionGetFlags ${DeepSeekQwen7BSec} $1
    IntOp $1 $1 & ${SECTION_OFF}
    SectionSetFlags ${DeepSeekQwen7BSec} $1

end:
FunctionEnd

Function SkipLicense
  ${IfNot} ${SectionIsSelected} ${HybridSec}
    abort  ;skip AMD license if hybrid was not enabled
  ${EndIf}
FunctionEnd


; MUI Settings
!insertmacro MUI_PAGE_WELCOME
!define MUI_COMPONENTSPAGE_SMALLDESC
!insertmacro MUI_PAGE_COMPONENTS

!define MUI_PAGE_CUSTOMFUNCTION_PRE SkipLicense
!insertmacro MUI_PAGE_LICENSE "AMD_LICENSE"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

!define MUI_PAGE_CUSTOMFUNCTION_SHOW .onSelChange




; Set the installer icon
Icon ${ICON_FILE}

; Language settings
LangString MUI_TEXT_WELCOME_INFO_TITLE "${LANG_ENGLISH}" "Welcome to the $LEMONADE_SERVER_STRING Installer"
LangString MUI_TEXT_WELCOME_INFO_TEXT "${LANG_ENGLISH}" "This wizard will install $LEMONADE_SERVER_STRING on your computer."
LangString MUI_TEXT_DIRECTORY_TITLE "${LANG_ENGLISH}" "Select Installation Directory"
LangString MUI_TEXT_INSTALLING_TITLE "${LANG_ENGLISH}" "Installing $LEMONADE_SERVER_STRING"
LangString MUI_TEXT_FINISH_TITLE "${LANG_ENGLISH}" "Installation Complete"
LangString MUI_TEXT_FINISH_SUBTITLE "${LANG_ENGLISH}" "Thank you for installing $LEMONADE_SERVER_STRING!"
LangString MUI_TEXT_ABORT_TITLE "${LANG_ENGLISH}" "Installation Aborted"
LangString MUI_TEXT_ABORT_SUBTITLE "${LANG_ENGLISH}" "Installation has been aborted."
LangString MUI_BUTTONTEXT_FINISH "${LANG_ENGLISH}" "Finish"
LangString MUI_TEXT_LICENSE_TITLE ${LANG_ENGLISH} "AMD License Agreement"
LangString MUI_TEXT_LICENSE_SUBTITLE ${LANG_ENGLISH} "Please review the license terms before installing AMD Ryzen AI Hybrid Execution Mode."
LangString DESC_SEC01 ${LANG_ENGLISH} "The minimum set of dependencies for a lemonade server that runs LLMs on CPU."
LangString DESC_HybridSec ${LANG_ENGLISH} "Add support for running LLMs on Ryzen AI hybrid execution mode. Only available on Ryzen AI 300-series processors."
LangString DESC_ModelsSec ${LANG_ENGLISH} "Select which models to install"
LangString DESC_Qwen05Sec ${LANG_ENGLISH} "Small CPU-only Qwen model"
LangString DESC_Llama1BSec ${LANG_ENGLISH} "1B parameter Llama model with hybrid execution"
LangString DESC_Llama3BSec ${LANG_ENGLISH} "3B parameter Llama model with hybrid execution"
LangString DESC_PhiSec ${LANG_ENGLISH} "Phi-3 Mini model with hybrid execution"
LangString DESC_Qwen7BSec ${LANG_ENGLISH} "7B parameter Qwen model with hybrid execution"
LangString DESC_DeepSeekLlama8BSec ${LANG_ENGLISH} "8B parameter DeepSeek Llama model with hybrid execution"
LangString DESC_DeepSeekQwen7BSec ${LANG_ENGLISH} "7B parameter DeepSeek Qwen model with hybrid execution"

; Insert the description macros
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} $(DESC_SEC01)
  !insertmacro MUI_DESCRIPTION_TEXT ${HybridSec} $(DESC_HybridSec)
  !insertmacro MUI_DESCRIPTION_TEXT ${ModelsSec} $(DESC_ModelsSec)
  !insertmacro MUI_DESCRIPTION_TEXT ${Qwen05Sec} $(DESC_Qwen05Sec)
  !insertmacro MUI_DESCRIPTION_TEXT ${Llama1BSec} $(DESC_Llama1BSec)
  !insertmacro MUI_DESCRIPTION_TEXT ${Llama3BSec} $(DESC_Llama3BSec)
  !insertmacro MUI_DESCRIPTION_TEXT ${PhiSec} $(DESC_PhiSec)
  !insertmacro MUI_DESCRIPTION_TEXT ${Qwen7BSec} $(DESC_Qwen7BSec)
  !insertmacro MUI_DESCRIPTION_TEXT ${DeepSeekLlama8BSec} $(DESC_DeepSeekLlama8BSec)
  !insertmacro MUI_DESCRIPTION_TEXT ${DeepSeekQwen7BSec} $(DESC_DeepSeekQwen7BSec)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Function .onInit
  StrCpy $LEMONADE_SERVER_STRING "Lemonade Server"
  StrCpy $HYBRID_SELECTED "true"
  
  ; Create a variable to store selected models
  StrCpy $9 ""  ; $9 will hold our list of selected models

  ; Set the install directory, allowing /D override from CLI install
  ${If} $InstDir != ""
    ; /D was used
  ${Else}
    ; Use the default
    StrCpy $InstDir "$LOCALAPPDATA\lemonade_server"
  ${EndIf}

  ; Check CPU name to determine if Hybrid section should be enabled
  DetailPrint "Checking CPU model..."
  
  ; Use registry query to get CPU name
  nsExec::ExecToStack 'reg query "HKEY_LOCAL_MACHINE\HARDWARE\DESCRIPTION\System\CentralProcessor\0" /v ProcessorNameString'
  Pop $0 ; Return value
  Pop $cpuName ; Output (CPU name)
  DetailPrint "Detected CPU: $cpuName"
  
  ; Check if CPU name contains "Ryzen AI" and a 3-digit number starting with 3
  StrCpy $isCpuSupported "false" ; Initialize CPU allowed flag to false
  
  ${StrLoc} $ryzenAiPos $cpuName "Ryzen AI" ">"
  ${If} $ryzenAiPos != ""
    ; Found "Ryzen AI", now look for 3xx series
    ${StrLoc} $seriesStartPos $cpuName " 3" ">"
    ${If} $seriesStartPos != ""
      ; Check if the character after "3" is a digit (first digit of model number)
      StrCpy $currentChar $cpuName 1 $seriesStartPos+2
      ${If} $currentChar >= "0"
        ${AndIf} $currentChar <= "9"
        ; Check if the character after that is also a digit (second digit of model number)
        StrCpy $currentChar $cpuName 1 $seriesStartPos+3
        ${If} $currentChar >= "0"
          ${AndIf} $currentChar <= "9"
          ; Check if the character after the third digit is a space or end of string
          StrCpy $currentChar $cpuName 1 $seriesStartPos+4
          ${If} $currentChar == " "
            ${OrIf} $currentChar == ""
            ; Found a complete 3-digit number starting with 3
            StrCpy $isCpuSupported "true"
            DetailPrint "Detected Ryzen AI 3xx series processor"
          ${EndIf}
        ${EndIf}
      ${EndIf}
    ${EndIf}
  ${EndIf}
  
  DetailPrint "CPU is compatible with Ryzen AI hybrid software: $isCpuSupported"
  
  ; Check if CPU is in the allowed models list
  ${If} $isCpuSupported != "true"
    ; Disable Hybrid section if CPU is not in allowed list
    SectionGetFlags ${HybridSec} $0
    IntOp $0 $0 & ${SECTION_OFF}    ; Turn off selection
    IntOp $0 $0 | ${SF_RO}          ; Make it read-only (can't be selected)
    SectionSetFlags ${HybridSec} $0
    StrCpy $HYBRID_SELECTED "false"
  ${EndIf}

  ; Disable hybrid mode by default in silent mode
  ; Use /Extras="hybrid" option to enable it
  ${If} ${Silent}
    
    ${GetParameters} $CMDLINE
    ${GetOptions} $CMDLINE "/Extras=" $HYBRID_CLI_OPTION

    ${IfNot} $HYBRID_CLI_OPTION == "hybrid"
      SectionSetFlags ${HybridSec} 0
      StrCpy $HYBRID_SELECTED "false"
    ${ElseIf} $isCpuSupported != "true"
      ; Don't allow hybrid mode if CPU is not in allowed list, even if specified in command line
      SectionSetFlags ${HybridSec} 0
      StrCpy $HYBRID_SELECTED "false"
    ${EndIf}
  ${EndIf}

  ; Call onSelChange to ensure initial model selection state is correct
  Call .onSelChange

FunctionEnd
```
### Lemonade Batch File
Lemonade uses "lemonade-server.bat":
```
@echo off
setlocal enabledelayedexpansion

REM --keep-alive is only used by the bash script to make sure that, if the server fails to open, we don't close the terminal right away.
REM Check for --keep-alive argument and remove it from arguments passed to CLI
set KEEP_ALIVE=0
set ARGS=
for %%a in (%*) do (
    if /I "%%a"=="--keep-alive" (
        set KEEP_ALIVE=1
    ) else (
        set ARGS=!ARGS! %%a
    )
)

REM Change to parent directory where conda env and bin folders are located
pushd "%~dp0.."

REM Run the Python CLI script through conda, passing filtered arguments
call "%CD%\python\Scripts\lemonade-server-dev" !ARGS!
popd

REM Error handling: Show message and pause if --keep-alive was specified
if %ERRORLEVEL% neq 0 (
    if %KEEP_ALIVE%==1 (
        echo.
        echo An error occurred while running Lemonade Server.
        echo Please check the error message above.
        echo.
        pause
    )
)
```