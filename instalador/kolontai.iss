;  Kolontái — instalador para Windows (Inno Setup 6.3 o posterior)
;  SPDX-License-Identifier: GPL-3.0-or-later
;
;  Uso:  ISCC.exe /DVersion=0.3.0 instalador\kolontai.iss
;  Requiere haber corrido antes: pyinstaller --noconfirm kolontai.spec
;  Este archivo se guarda en UTF-8 con BOM para que Inno respete las tildes.

#ifndef Version
  #define Version "0.0.0"
#endif

[Setup]
; No cambiar AppId: así las versiones nuevas se instalan encima de las viejas
AppId={{1946CDFE-AC44-42EF-ACBA-939A25D5D0AB}
AppName=Kolontái
AppVersion={#Version}
AppVerName=Kolontái {#Version}
AppPublisher=Juan Sebastián Berrío Posada
AppCopyright=© 2026 Juan Sebastián Berrío Posada · GPL-3.0-or-later
DefaultDirName={autopf}\Kolontai
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=salida
OutputBaseFilename=Kolontai-{#Version}-instalador
SetupIconFile=..\kolontai\recursos\kolontai.ico
UninstallDisplayIcon={app}\Kolontai.exe
UninstallDisplayName=Kolontái
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Se puede instalar sin permisos de administrador (solo para el usuario actual)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Kolontai\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Kolontái"; Filename: "{app}\Kolontai.exe"
Name: "{autodesktop}\Kolontái"; Filename: "{app}\Kolontai.exe"; Tasks: escritorio

[Run]
Filename: "{app}\Kolontai.exe"; Description: "{cm:LaunchProgram,Kolontái}"; Flags: nowait postinstall skipifsilent
