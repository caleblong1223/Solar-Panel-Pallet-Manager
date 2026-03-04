; NSIS Installer Script for Windows
; Creates a professional installer wizard

!define APP_NAME "Pallet Manager"
!define APP_VERSION "2.0.0"
!define APP_PUBLISHER "Crossroads Solar"
!define APP_EXE "Pallet Manager.exe"
!define APP_EXE_SOURCE "dist\Pallet Manager.exe"
!define APP_INSTALL_DIR "$PROGRAMFILES\${APP_NAME}"

; Modern UI
!include "MUI2.nsh"

; Installer attributes
Name "${APP_NAME}"
OutFile "dist\${APP_NAME}-Setup.exe"
InstallDir "${APP_INSTALL_DIR}"
RequestExecutionLevel admin
Unicode True

; Compression settings - LZMA for best compression
SetCompressor /SOLID lzma
SetCompressorDictSize 32

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "installer_license.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer sections
Section "Main Application" SecMain
    SectionIn RO

    ; Set output path
    SetOutPath "$INSTDIR"

    ; EXE is embedded at installer build-time.
    File "${APP_EXE_SOURCE}"

    ; Create application directory structure
    CreateDirectory "$INSTDIR\data"
    CreateDirectory "$INSTDIR\assets"
    CreateDirectory "$INSTDIR\docs"

    ; Copy data directory (required for application to work)
    DetailPrint "Installing application data files..."
    File /r "data\*.*"

    ; Copy assets
    DetailPrint "Installing application assets..."
    File /r "assets\*.*"

    ; Copy documentation (optional but helpful)
    DetailPrint "Installing documentation..."
    File /r "docs\*.*"

    ; Copy tools directory if it exists (for SumatraPDF)
    IfFileExists "tools" 0 +4
        CreateDirectory "$INSTDIR\tools"
        DetailPrint "Installing external tools..."
        File /r "tools\*.*"

    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Write registry keys
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "InstallLocation" "$INSTDIR"
SectionEnd

Section "Start Menu Shortcut" SecStartMenu
    ; Already created in main section
SectionEnd

Section "Desktop Shortcut" SecDesktop
    ; Already created in main section
SectionEnd

; Section descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Installs ${APP_NAME} and required files."
    !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Creates a shortcut in the Start Menu."
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Creates a shortcut on the Desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller
Section "Uninstall"
    ; Remove main executable
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\Uninstall.exe"

    ; Remove data directory and all contents
    RMDir /r "$INSTDIR\data"

    ; Remove assets directory and all contents
    RMDir /r "$INSTDIR\assets"

    ; Remove docs directory and all contents
    RMDir /r "$INSTDIR\docs"

    ; Remove tools directory and all contents (if exists)
    RMDir /r "$INSTDIR\tools"

    ; Remove any remaining files in the install directory
    Delete "$INSTDIR\*.*"

    ; Remove shortcuts
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

    ; Remove install directory (only if empty)
    RMDir "$INSTDIR"
SectionEnd
