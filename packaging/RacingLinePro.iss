#ifndef AppVersion
  #define AppVersion "2.4.6"
#endif

#define ProjectRoot SourcePath + "\.."
#define PortableDir ProjectRoot + "\dist\RacingLinePro-v" + AppVersion

[Setup]
AppId={{1230548E-AB95-4995-85EF-B723E78F5438}
AppName=Racing Line Pro
AppVersion={#AppVersion}
AppPublisher=tzt302
AppPublisherURL=https://github.com/tzt302/game_racing
AppSupportURL=https://github.com/tzt302/game_racing/issues
AppUpdatesURL=https://github.com/tzt302/game_racing/releases
DefaultDirName={localappdata}\Programs\Racing Line Pro
DefaultGroupName=Racing Line Pro
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#ProjectRoot}\dist
OutputBaseFilename=RacingLinePro-v{#AppVersion}-Setup
Compression=lzma2/max
SolidCompression=no
WizardStyle=modern
UninstallDisplayIcon={app}\RacingLinePro.exe
VersionInfoVersion={#AppVersion}.0
VersionInfoProductName=Racing Line Pro
VersionInfoProductVersion={#AppVersion}
VersionInfoCompany=tzt302
VersionInfoDescription=Racing Line Pro installer

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#PortableDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Racing Line Pro"; Filename: "{app}\RacingLinePro.exe"
Name: "{autodesktop}\Racing Line Pro"; Filename: "{app}\RacingLinePro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RacingLinePro.exe"; Description: "{cm:LaunchProgram,Racing Line Pro}"; Flags: nowait postinstall skipifsilent
