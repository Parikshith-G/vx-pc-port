; ==============================================================================
; VX Player PC - Modern NSIS Installer Script
; ==============================================================================

!include "MUI2.nsh"
!include "FileFunc.nsh"

; General Definitions
Name "VX Player"
OutFile "dist\VXPlayerSetup.exe"
Unicode True
RequestExecutionLevel user ; User-level install: no UAC elevation needed

; Default Installation Directory: %LocalAppData%\Programs\VX Player
InstallDir "$LOCALAPPDATA\Programs\VX Player"
InstallDirRegKey HKCU "Software\VXPlayer" "InstallDir"

; Version Information
VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "VX Player"
VIAddVersionKey "CompanyName" "Parikshith G"
VIAddVersionKey "LegalCopyright" "MIT License"
VIAddVersionKey "FileDescription" "VX Player Installer"
VIAddVersionKey "FileVersion" "1.0.0.0"
VIAddVersionKey "ProductVersion" "1.0.0"

; Interface Configuration
!define MUI_ICON "app_icon.ico"
!define MUI_UNICON "app_icon.ico"
!define MUI_ABORTWARNING

; Welcome Page
!define MUI_WELCOMEPAGE_TITLE "Welcome to VX Player Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of VX Player (PC Port).$\r$\n$\r$\nVX Player is a high-performance offline desktop video player built with LibVLC, featuring hold-to-boost playback speed, 90s OP skip, natural episode sorting, and smart resume history.$\r$\n$\r$\nClick Next to continue."
!insertmacro MUI_PAGE_WELCOME

; Directory Selection Page
!insertmacro MUI_PAGE_DIRECTORY

; Components / Shortcuts Page
!define MUI_PAGE_HEADER_TEXT "Choose Shortcuts"
!define MUI_PAGE_HEADER_SUBTEXT "Choose where to create shortcuts for VX Player."
!insertmacro MUI_PAGE_COMPONENTS

; Installation Progress Page
!insertmacro MUI_PAGE_INSTFILES

; Finish Page
!define MUI_FINISHPAGE_RUN "$INSTDIR\VXPlayerPC.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch VX Player now"
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; ------------------------------------------------------------------------------
; Installer Sections
; ------------------------------------------------------------------------------

Section "!Core Application" SecCore
    SectionIn RO ; Read-only, mandatory

    SetOutPath "$INSTDIR"

    ; Copy Application Files
    File "dist\VXPlayerPC.exe"
    File "app_icon.ico"
    File "README.md"

    ; Write installation path to registry
    WriteRegStr HKCU "Software\VXPlayer" "InstallDir" "$INSTDIR"

    ; Create Uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Register in Windows "Installed Apps" / "Apps & Features" (Add or Remove Programs)
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "DisplayName" "VX Player"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "DisplayVersion" "1.0.0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "Publisher" "Parikshith G"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "DisplayIcon" "$INSTDIR\VXPlayerPC.exe,0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "URLInfoAbout" "https://github.com/Parikshith-G/vx-pc-port"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "NoRepair" 1

    ; Estimate Size in KB (~31 MB)
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer" "EstimatedSize" "$0"
SectionEnd

Section "Start Menu Shortcut" SecStartMenu
    CreateDirectory "$SMPROGRAMS\VX Player"
    CreateShortcut "$SMPROGRAMS\VX Player\VX Player.lnk" "$INSTDIR\VXPlayerPC.exe" "" "$INSTDIR\VXPlayerPC.exe" 0
    CreateShortcut "$SMPROGRAMS\VX Player\Uninstall VX Player.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0
SectionEnd

Section "Desktop Shortcut" SecDesktop
    CreateShortcut "$DESKTOP\VX Player.lnk" "$INSTDIR\VXPlayerPC.exe" "" "$INSTDIR\VXPlayerPC.exe" 0
SectionEnd

; Section descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Core application binaries and resources."
    !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Creates shortcuts in the Windows Start Menu and Search."
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Creates a shortcut on your Desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ------------------------------------------------------------------------------
; Uninstaller Section
; ------------------------------------------------------------------------------

Section "Uninstall"
    ; Remove Shortcuts
    Delete "$DESKTOP\VX Player.lnk"
    Delete "$SMPROGRAMS\VX Player\VX Player.lnk"
    Delete "$SMPROGRAMS\VX Player\Uninstall VX Player.lnk"
    RMDir "$SMPROGRAMS\VX Player"

    ; Remove Installed Files
    Delete "$INSTDIR\VXPlayerPC.exe"
    Delete "$INSTDIR\app_icon.ico"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\Uninstall.exe"

    ; Remove Directory if empty
    RMDir "$INSTDIR"

    ; Remove Registry Keys
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXPlayer"
    DeleteRegKey HKCU "Software\VXPlayer"
SectionEnd
