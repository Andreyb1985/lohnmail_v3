// CI-only legacy-layout writer. Never included in the released MSIX.
// Reproduces the pre-2.1.1 logical AppData writes under genuine package identity.
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
class LegacyStorageFixture {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
    static extern int GetCurrentPackageFamilyName(ref uint length, StringBuilder name);
    static int Main(string[] args) {
        if (Environment.GetEnvironmentVariable("GITHUB_ACTIONS") != "true" || args.Length != 2) return 2;
        uint length = 0;
        if (GetCurrentPackageFamilyName(ref length, null) != 122) return 3;
        var family = new StringBuilder((int)length);
        if (GetCurrentPackageFamilyName(ref length, family) != 0) return 4;
        string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LohnMail");
        if (args[1] != "empty") {
            Directory.CreateDirectory(Path.Combine(root, "Settings"));
            Directory.CreateDirectory(Path.Combine(root, "Companies", "CI-Legacy-Unique"));
            File.WriteAllText(Path.Combine(root, "Settings", "license.json"), "{\"license_key\":\"SYNTHETIC-KEEP\",\"device_id\":\"SYNTHETIC-DEVICE\"}");
            File.WriteAllText(Path.Combine(root, "Settings", "machine_id"), "SYNTHETIC-DEVICE");
            File.WriteAllText(Path.Combine(root, "Settings", "secrets.dat"), "SYNTHETIC-ENCRYPTED-NOT-A-PASSWORD");
            File.WriteAllText(Path.Combine(root, "Companies", "CI-Legacy-Unique", "result.pdf"), "SYNTHETIC-PDF");
            File.WriteAllText(Path.Combine(root, "Companies", "CI-Legacy-Unique", "audit_check.xlsx"), "SYNTHETIC-XLSX");
        } else Directory.CreateDirectory(root);
        File.WriteAllText(args[0], family.ToString());
        return 0;
    }
}
