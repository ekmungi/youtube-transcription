; Inno Setup script for YT Transcribe
; Compile with: iscc installer.iss

#define MyAppName "YT Transcribe"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "ekmungi"
#define MyAppURL "https://github.com/ekmungi/youtube-transcription"
#define MyAppExeName "YT Transcribe.exe"
#define MyMcpServerExeName "yt-transcribe-server.exe"

[Setup]
AppId={{B2F7A3E1-4D5C-4A8B-9E6F-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output installer to dist/
OutputDir=dist
OutputBaseFilename=YT-Transcribe-Setup-{#MyAppVersion}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Install per-user, no admin required
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
; Modern installer look
WizardStyle=modern
; App icon
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\YT Transcribe.exe
; Minimum Windows 10
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenu"; Description: "Create a Start Menu shortcut"; GroupDescription: "{cm:AdditionalIcons}"
Name: "mcpconfig"; Description: "Register MCP server with Claude Code"; GroupDescription: "Claude Code Integration"

[Files]
; Include everything from PyInstaller dist folder (GUI + MCP server exes)
Source: "dist\YT Transcribe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; MCP registration scripts
Source: "scripts\register-mcp.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "scripts\unregister-mcp.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut (per-user)
Name: "{userprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (optional, per-user)
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Option to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
; Register MCP server with Claude Code (writes to ~/.claude.json)
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\register-mcp.ps1"" -ServerPath ""{app}\{#MyMcpServerExeName}"""; Tasks: mcpconfig; Flags: runhidden

[UninstallRun]
; Unregister MCP server from Claude Code on uninstall
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\unregister-mcp.ps1"""; Flags: runhidden

[UninstallDelete]
; Clean up config on uninstall (optional -- ask user)
Type: dirifempty; Name: "{userappdata}\.yt-transcribe"
