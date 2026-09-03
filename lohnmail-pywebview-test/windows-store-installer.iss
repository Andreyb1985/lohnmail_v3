#ifndef AppVersion
  #define AppVersion "2.0.3"
#endif
#ifndef AppBuild
  #define AppBuild "2026.09.03.1"
#endif
#ifndef AppNumericVersion
  #define AppNumericVersion "2.0.3.4"
#endif

#define AppName "LohnMail"
#define AppPublisher "LohnMail"
#define AppExeName "LohnMail.exe"

[Setup]
AppId={{A804EBDD-BF78-49DD-96A7-5B5986B71B1B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppNumericVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=LohnMail Installer
VersionInfoProductName={#AppName}
DefaultDirName={localappdata}\Programs\LohnMail
DefaultGroupName=LohnMail
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=release\store
OutputBaseFilename=LohnMail-{#AppVersion}-build-{#AppBuild}-Setup-x64
SetupIconFile=web\assets\brand\LohnMail.ico
UninstallDisplayIcon={app}\LohnMail.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
CloseApplicationsFilter=LohnMail.exe,LohnMail.RootLauncher.exe
UsePreviousAppDir=yes
UsePreviousGroup=yes
ChangesAssociations=no
ChangesEnvironment=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[InstallDelete]
; Only replace program binaries. Local settings, companies, license data,
; SQLite history and generated reports live outside App and are preserved.
Type: filesandordirs; Name: "{app}\App"

[Dirs]
Name: "{app}\Settings"; Flags: uninsneveruninstall
Name: "{app}\Companies"; Flags: uninsneveruninstall

[Files]
Source: "release\LohnMail\App\*"; DestDir: "{app}\App"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "release\LohnMail\LohnMail.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\LohnMail\README-WINDOWS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\LohnMail\Settings\settings.json"; DestDir: "{app}\Settings"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\LohnMail"; Filename: "{app}\LohnMail.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\LohnMail"; Filename: "{app}\LohnMail.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\LohnMail.exe"; Description: "LohnMail starten"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

