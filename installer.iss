[Setup]
AppName=Kypseli
AppVersion=0.6.2
DefaultDirName={autopf}\Kypseli
DefaultGroupName=Kypseli
UninstallDisplayIcon={app}\kypseli.exe
Compression=lzma
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=kypseli-setup

[Files]
Source: "dist\kypseli.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Kypseli"; Filename: "{app}\kypseli.exe"

[Code]
// This part adds Kypseli to the Windows PATH automatically
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