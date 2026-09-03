LohnMail 2.0.3 - Windows pywebview (Build 2026.09.03.1)
=================================

Ordnerstruktur:

  LohnMail.exe
    Empfohlener Programmstart direkt aus dem Hauptordner

  App\
    Interne Programmdateien; beim Update wird nur dieser Ordner ersetzt

  Settings\
    settings.json
    Lizenzdaten, Verlauf und gespeicherte Sitzungen entstehen erst beim Start

  Companies\
    Lohn_<Unternehmensname>\
      PDF-, Excel- und Versandberichte

Start der fertigen Windows-Version:

  LohnMail.exe im Hauptordner doppelklicken.

Erster Start aus dem Quellpaket mit installiertem Python:

  INSTALL-AND-START-WINDOWS.cmd doppelklicken.

Empfohlen werden Python 3.12 oder 3.13 und Microsoft Edge WebView2. Unter
Windows 10 und Windows 11 ist WebView2 normalerweise bereits installiert.
Beim ersten Start werden die Python-Umgebung und Abhängigkeiten im App-Ordner
installiert. Outlook-Versand benötigt Outlook Classic und ein geöffnetes,
vollständig verbundenes Outlook-Profil. Das neue Outlook wird nicht unterstützt.

EXE auf Windows erstellen:

  PowerShell im Projektordner öffnen und .\BUILD-WINDOWS.ps1 ausführen.

Danach liegt die geprüfte portable Struktur unter release\LohnMail.
Settings und Companies liegen neben dem Launcher und werden durch Updates nicht ersetzt.

Autonomen Microsoft-Store-Installer erstellen:

  1. Inno Setup 6 installieren.
  2. .\BUILD-WINDOWS.ps1 ausführen.
  3. .\BUILD-STORE-INSTALLER.ps1 ausführen.

Der Offline-Installer liegt danach unter release\store. Er installiert LohnMail
pro Benutzer unter %%LOCALAPPDATA%%\Programs\LohnMail. Bei einer Installation über
eine vorhandene Version werden nur die Programmdateien in App ersetzt. Settings,
Companies, Lizenzdaten, SQLite-Verlauf und Berichte bleiben erhalten.

Parameter für die stille Installation:

  /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-

Vor der Einreichung im Microsoft Store müssen die EXE-Dateien und der Installer
mit einem vertrauenswürdigen Code-Signing-Zertifikat signiert werden.
