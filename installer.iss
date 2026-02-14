; Kypseli Windows Installer
; Inno Setup Script

[Setup]
AppName=Kypseli
AppVersion=0.7.7
AppPublisher=Ioannis Roumeliotis
AppPublisherURL=https://github.com/IoanRoume/kypseli
AppSupportURL=https://github.com/IoanRoume/kypseli/issues
AppUpdatesURL=https://github.com/IoanRoume/kypseli/releases
DefaultDirName={autopf}\Kypseli
DefaultGroupName=Kypseli
AllowNoIcons=yes
; License file
LicenseFile=LICENSE
; Output settings
OutputDir=installer_output
OutputBaseFilename=kypseli-setup
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Installer appearance
SetupIconFile=assets\logo.ico
WizardStyle=modern
WizardImageFile=assets\wizard-large.bmp
WizardSmallImageFile=assets\wizard-small.bmp
; Uninstaller icon
UninstallDisplayIcon={app}\kypseli.exe
; Privileges
PrivilegesRequired=admin
; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Add Kypseli to system PATH"; GroupDescription: "System Integration:"; Flags: checkedonce

[Files]
; Main application files
Source: "dist\kypseli\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Logo for uninstaller
Source: "assets\logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Kypseli"; Filename: "{app}\kypseli.exe"; IconFilename: "{app}\logo.ico"
Name: "{group}\{cm:UninstallProgram,Kypseli}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Kypseli"; Filename: "{app}\kypseli.exe"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Registry]
; Add to PATH
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath('{app}')

[Run]
Filename: "{app}\kypseli.exe"; Parameters: "version"; Description: "Verify installation"; Flags: postinstall nowait skipifsilent shellexec

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Path: string;
  AppPath: string;
  P: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path) then
    begin
      AppPath := ExpandConstant('{app}');
      P := Pos(';' + AppPath, Path);
      if P > 0 then
      begin
        Delete(Path, P, Length(';' + AppPath));
        RegWriteStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path);
      end;
    end;
  end;
end;