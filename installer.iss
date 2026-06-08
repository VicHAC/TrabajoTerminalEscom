[Setup]
AppName=AVA Image Analytics
AppVersion=1.0
AppPublisher=Escuela Superior de Computo
DefaultDirName={autopf}\AVA Image Analytics
DefaultGroupName=AVA Image Analytics
OutputDir=build
OutputBaseFilename=Instalar_AVA_Image_Analytics
Compression=lzma2/fast
SolidCompression=no
SetupIconFile=assets\logoW.ico
UninstallDisplayIcon={app}\AVA_Image_Analytics.exe
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Incluir el ejecutable y todo el contenido de la carpeta dist/AVA_Image_Analytics
Source: "dist\AVA_Image_Analytics\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AVA Image Analytics"; Filename: "{app}\AVA_Image_Analytics.exe"
Name: "{autodesktop}\AVA Image Analytics"; Filename: "{app}\AVA_Image_Analytics.exe"; Tasks: desktopicon; IconFilename: "{app}\assets\logoW.ico"

[Run]
Filename: "{app}\AVA_Image_Analytics.exe"; Description: "{cm:LaunchProgram,AVA Image Analytics}"; Flags: nowait postinstall skipifsilent
