using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class LohnMailRootLauncher
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        string rootDirectory = AppDomain.CurrentDomain.BaseDirectory;
        string appExecutable = Path.Combine(rootDirectory, "App", "LohnMail.exe");
        if (!File.Exists(appExecutable))
        {
            MessageBox.Show(
                "Der Programmordner App oder LohnMail.exe wurde nicht gefunden. Bitte stellen Sie die vollständige LohnMail-Struktur wieder her.",
                "LohnMail konnte nicht gestartet werden",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
            return;
        }

        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = appExecutable,
                WorkingDirectory = Path.GetDirectoryName(appExecutable),
                UseShellExecute = true
            });
        }
        catch (Exception)
        {
            MessageBox.Show(
                "LohnMail konnte nicht gestartet werden. Bitte prüfen Sie die Zugriffsrechte und versuchen Sie es erneut.",
                "LohnMail konnte nicht gestartet werden",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
        }
    }
}
