[Setup]
AppName=Kypseli
AppVersion=0.7.0
DefaultDirName={autopf}\Kypseli
DefaultGroupName=Kypseli
UninstallDisplayIcon={app}\kypseli.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer_output
OutputBaseFilename=kypseli-setup

[Files]
; Copy the entire kypseli folder contents
Source: "dist\kypseli\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Kypseli"; Filename: "{app}\kypseli.exe"
Name: "{commondesktop}\Kypseli"; Filename: "{app}\kypseli.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
    Path: string;
begin
    if CurStep = ssPostInstall then
    begin
        if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
        begin
            if Pos(ExpandConstant('{app}'), Path) = 0 then
            begin
                RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path + ';' + ExpandConstant('{app}'));
            end;
        end;
    end;
end;