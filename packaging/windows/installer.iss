#define MyAppName "Phone Remote"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "BigFFFF"
#define MyAppExeName "PhoneRemote.exe"
#define ApiRuleName "Phone Remote API"
#define DiscoveryRuleName "Phone Remote Discovery"

[Setup]
AppId={{DE0769D4-51A1-41B8-864A-5B5CCB1F47B7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Phone Remote
DefaultGroupName=Phone Remote
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=PhoneRemoteSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
SetupMutex=PhoneRemote-Setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start Phone Remote with Windows"; GroupDescription: "Startup"; Flags: checkedonce

[Files]
Source: "..\..\dist\PhoneRemote.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Phone Remote"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall Phone Remote"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Phone Remote"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; StatusMsg: "Stopping an existing Phone Remote process..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#ApiRuleName}"""; Flags: runhidden
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#DiscoveryRuleName}"""; Flags: runhidden
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#ApiRuleName}"" dir=in action=allow program=""{app}\{#MyAppExeName}"" protocol=TCP localport=8765,8766 profile=private remoteip=LocalSubnet enable=yes"; Flags: runhidden; StatusMsg: "Configuring the Private-network API and Web Remote firewall rule..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#DiscoveryRuleName}"" dir=in action=allow program=""{app}\{#MyAppExeName}"" protocol=UDP localport=5353 profile=private remoteip=LocalSubnet enable=yes"; Flags: runhidden; StatusMsg: "Configuring the Private-network discovery firewall rule..."
Filename: "{app}\{#MyAppExeName}"; Parameters: "--install-startup"; Flags: runhidden runasoriginaluser; Tasks: startup; StatusMsg: "Registering per-user startup..."
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Phone Remote"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--remove-startup"; Flags: runhidden; RunOnceId: "RemoveStartup"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "StopPhoneRemote"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#ApiRuleName}"""; Flags: runhidden; RunOnceId: "RemoveApiRule"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#DiscoveryRuleName}"""; Flags: runhidden; RunOnceId: "RemoveDiscoveryRule"

[Code]
var
  RemoveUserData: Boolean;

function InitializeUninstall(): Boolean;
begin
  RemoveUserData := MsgBox(
    'Remove paired devices, server identity, settings, and logs?' + #13#10 +
    'Choose No to preserve them for a future reinstall.',
    mbConfirmation, MB_YESNO) = IDYES;
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveUserData then
    DelTree(ExpandConstant('{localappdata}\PhoneRemote'), True, True, True);
end;
