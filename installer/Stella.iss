; Stella Evo — Windows installer (Inno Setup)
; ---------------------------------------------------------------------------
; Built by scripts/stella_build.py via:
;     ISCC /DMyAppVersion=1.2.3 /DMySourceDir="C:\...\dist\StellaEvo" installer\Stella.iss
;
; MySourceDir is the PyInstaller COLLECT output (onedir): it already contains
; StellaEvo.exe plus the bundled Python runtime and assets. We copy that whole
; folder into Program Files and put an uninstaller + shortcuts next to it, so
; the app runs exactly as the portable zip does — just with a Start Menu entry,
; a Desktop shortcut, and a clean Add/Remove Programs entry.
;
; Requires ISCC (Inno Setup 6) on PATH. If it isn't, stella_build.py skips the
; .exe and keeps the portable zip instead — nothing silently no-ops.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef MySourceDir
  #define MySourceDir "..\dist\StellaEvo"
#endif

#define MyAppName "Stella AI Evo"
#define MyAppExeName "StellaEvo.exe"
#define MyAppAssocName MyAppName + " Session"
#define MyAppPublisher "Prabha Solutions"
#define MyAppURL "https://github.com/Emma-Keaton/stella"

[Setup]
; Same GUID across releases so upgrades replace the previous install in place
; instead of side-by-side duplicates. Change only on a packaging ground-up.
AppId={{8E4A1C0F-2B6D-4A7E-9C31-STELLAEVO0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Emit to installer\Output so stella_build.py finds StellaSetup-<version>.exe
OutputDir=..\installer\Output
OutputBaseFilename=StellaSetup-{#MyAppVersion}
SetupIconFile=..\assets\stella_logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; x64 and arm64 Windows desktops both run x64 PyInstaller builds; also allow 32-bit.
ArchitecturesAllowed=x64compatible arm64
ArchitecturesInstallIn64BitMode=x64compatible arm64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The entire onedir payload. Everything ships as data so it is overwritten and
; removed cleanly on upgrade/uninstall. 'recursesubdirs' grabs assets/, base_library.zip,
; and the bundled Python interpreter DLLs.
Source: "{#MySourceDir}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; \
    Flags: nowait postinstall skipifsilent
