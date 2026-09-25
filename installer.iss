; Inno Setup script for Excel Processor.
; Build the app first (python scripts/build.py), then compile this with:
;   iscc installer.iss
; Produces a single dist\ExcelProcessor-Setup.exe. Re-running the installer
; on a future version (same AppId, higher AppVersion) upgrades in place —
; that's the whole update story: rebuild, recompile, hand over the new exe.

; MyAppVersion is passed in as /DMyAppVersion=X.Y.Z by scripts/build_installer.py
; (read from scripts/app_info.py so the installer version always matches the app).
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppId={{03BC034A-9F0E-43D0-9CDC-4A0BD3F38429}}
AppName=Excel Processor
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\ExcelProcessor
DefaultGroupName=Excel Processor
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=ExcelProcessor-Setup
SetupIconFile=app\assets\icons\excel-processor-icon.ico
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\app\assets\icons\excel-processor-icon.ico
ChangesAssociations=yes

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: checkedonce

[Files]
Source: "dist\ExcelProcessor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Excel Processor"; Filename: "{app}\ExcelProcessor.exe"; IconFilename: "{app}\app\assets\icons\excel-processor-icon.ico"
Name: "{userdesktop}\Excel Processor"; Filename: "{app}\ExcelProcessor.exe"; IconFilename: "{app}\app\assets\icons\excel-processor-icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\ExcelProcessor.exe"; Description: "Launch Excel Processor now"; Flags: postinstall nowait skipifsilent
