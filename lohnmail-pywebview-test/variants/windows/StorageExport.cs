// One-time, copy-only legacy MSIX migration. No network, shell or elevation.
// GetCurrentPackageFamilyName == APPMODEL_ERROR_NO_PACKAGE is mandatory BEFORE
// reading AppData. Never infer absence of virtualization from an executable path.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

class StorageExport {
    static JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = Int32.MaxValue, RecursionLimit = 100 };
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern int GetCurrentPackageFamilyName(ref uint size, IntPtr name);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool InitializeProcThreadAttributeList(IntPtr list, int count, int flags, ref IntPtr size);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool UpdateProcThreadAttribute(IntPtr list, uint flags, IntPtr key, IntPtr value, IntPtr size, IntPtr previous, IntPtr returned);
    [DllImport("kernel32.dll")] static extern void DeleteProcThreadAttributeList(IntPtr list);
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateProcess(string app, StringBuilder command, IntPtr pa, IntPtr ta, bool inherit, uint flags, IntPtr env, string cwd, ref StartupEx startup, out ProcessInfo process);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", SetLastError = true)] static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool GetExitCodeProcess(IntPtr handle, out uint code);
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct Startup {
        public int cb; public string reserved, desktop, title;
        public uint x, y, width, height, charsX, charsY, fill, flags;
        public ushort show, reservedSize; public IntPtr reservedBytes, input, output, error;
    }
    [StructLayout(LayoutKind.Sequential)] struct StartupEx { public Startup start; public IntPtr attributes; }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo { public IntPtr process, thread; public uint pid, tid; }

    static int Breakaway(string request, int depth) {
        // Documented Win10 1703+ desktop-app policy. The descendant also checks
        // its own identity; policy success alone is NOT evidence of breakaway.
        IntPtr size = IntPtr.Zero;
        InitializeProcThreadAttributeList(IntPtr.Zero, 1, 0, ref size);
        IntPtr list = Marshal.AllocHGlobal(size), policy = Marshal.AllocHGlobal(4);
        bool initialized = false;
        try {
            if (!InitializeProcThreadAttributeList(list, 1, 0, ref size)) throw new Win32Exception();
            initialized = true;
            Marshal.WriteInt32(policy, 1); // BREAKAWAY_ENABLE_PROCESS_TREE
            if (!UpdateProcThreadAttribute(list, 0, new IntPtr(0x20012), policy, new IntPtr(4), IntPtr.Zero, IntPtr.Zero)) throw new Win32Exception();
            StartupEx startup = new StartupEx(); startup.start.cb = Marshal.SizeOf(startup); startup.attributes = list;
            string exe = Process.GetCurrentProcess().MainModule.FileName;
            // Windows paths cannot contain a quote. No shell interprets these arguments.
            StringBuilder command = new StringBuilder("\"" + exe + "\" \"" + request + "\" " + depth);
            ProcessInfo process;
            if (!CreateProcess(exe, command, IntPtr.Zero, IntPtr.Zero, false, 0x08080000, IntPtr.Zero, Path.GetDirectoryName(request), ref startup, out process)) throw new Win32Exception();
            try {
                if (WaitForSingleObject(process.process, 0xFFFFFFFF) != 0) throw new Win32Exception();
                uint code;
                if (!GetExitCodeProcess(process.process, out code)) throw new Win32Exception();
                return (int)code;
            } finally { CloseHandle(process.thread); CloseHandle(process.process); }
        } finally {
            if (initialized) DeleteProcThreadAttributeList(list);
            Marshal.FreeHGlobal(policy); Marshal.FreeHGlobal(list);
        }
    }

    static void WriteJson(string path, object value) {
        string temp = path + "." + Guid.NewGuid().ToString("N");
        using (FileStream stream = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None)) {
            byte[] bytes = new UTF8Encoding(false).GetBytes(Json.Serialize(value));
            stream.Write(bytes, 0, bytes.Length); stream.Flush(true);
        }
        File.Move(temp, path); // never replace another completed snapshot
    }
    static string Hash(Stream stream) {
        stream.Position = 0;
        using (SHA256 algorithm = SHA256.Create()) {
            return BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
    }
    static void NoLinks(string path) {
        for (DirectoryInfo dir = new DirectoryInfo(path); dir != null; dir = dir.Parent)
            if (dir.Exists && (dir.Attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("Verknuepfung nicht erlaubt: " + dir.FullName);
    }
    static List<string> Files(string root) {
        NoLinks(root);
        List<string> files = new List<string>();
        if (File.Exists(root)) throw new IOException("Datenpfad ist keine Ordner: " + root);
        if (!Directory.Exists(root)) return files;
        Stack<string> dirs = new Stack<string>(); dirs.Push(root);
        while (dirs.Count > 0) {
            string dir = dirs.Pop();
            foreach (string path in Directory.GetFileSystemEntries(dir)) {
                FileAttributes attributes = File.GetAttributes(path);
                if ((attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("Verknuepfung nicht erlaubt: " + path);
                if ((attributes & FileAttributes.Directory) != 0) dirs.Push(path); else files.Add(path);
            }
        }
        return files;
    }
    static Dictionary<string, string> Inventory(string root) {
        Dictionary<string, string> result = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (string path in Files(root)) using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
            result.Add(path.Substring(root.Length + 1).Replace('\\', '/'), Hash(stream));
        return result;
    }
    static void Same(Dictionary<string, string> a, Dictionary<string, string> b) {
        if (a.Count != b.Count) throw new IOException("Daten wurden geaendert. Originaldaten bleiben erhalten.");
        foreach (var pair in a) if (!b.ContainsKey(pair.Key) || b[pair.Key] != pair.Value)
            throw new IOException("Kopie nicht bestaetigt: " + pair.Key);
    }
    static string Full(string path) { return Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar); }
    static bool Equal(string a, string b) { return String.Equals(Full(a), Full(b), StringComparison.OrdinalIgnoreCase); }

    static void Export(Dictionary<string, object> request) {
        string local = Full(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData));
        string family = (string)request["family"], workspace = Full((string)request["workspace"]);
        if (family.IndexOfAny(new char[] {'/', '\\', ':'}) >= 0 || family == "..") throw new IOException("Ungueltige Paketfamilie.");
        string cache = Path.Combine(local, "Packages", family, "LocalCache");
        if (!Equal(local, (string)request["local"]) || !Equal(cache, (string)request["cache"])) throw new IOException("Windows-Speicherpfade stimmen nicht ueberein.");
        string appData = Directory.GetParent(local).FullName;
        if (Equal(workspace, appData) || workspace.StartsWith(appData + "\\", StringComparison.OrdinalIgnoreCase)) throw new IOException("Arbeitsordner muss ausserhalb AppData liegen.");
        NoLinks(workspace);
        int parent = Convert.ToInt32(request["parent"]);
        using (Process owner = Process.GetProcessById(parent)) {
            if (owner.ProcessName != "LohnMail") throw new IOException("Migration muss von LohnMail gestartet werden.");
        }
        foreach (Process app in Process.GetProcessesByName("LohnMail")) using (app) {
            if (app.Id != parent) throw new IOException("Bitte andere LohnMail-Instanzen schliessen und erneut starten.");
        }
        string direct = Path.Combine(local, "Programs", "LohnMail");
        if (Files(Path.Combine(direct, "Settings")).Count > 0 || Files(Path.Combine(direct, "Companies")).Count > 0)
            throw new IOException("Zusaetzliche direkte Installation gefunden: " + direct + ". Bitte Support kontaktieren.");
        var roots = new Dictionary<string, string> {
            {"ordinary", Path.Combine(local, "LohnMail")}, {"redirected", Path.Combine(cache, "Local", "LohnMail")}
        };
        string target = Path.Combine(workspace, "LohnMail-Legacy-Export");
        // Stable read handles prevent writes/deletes to existing files throughout
        // the snapshot. Re-enumeration catches new files. Originals are read-only.
        var handles = new Dictionary<string, Dictionary<string, FileStream>>();
        try {
            foreach (var root in roots) {
                var streams = new Dictionary<string, FileStream>(); handles.Add(root.Key, streams);
                foreach (string path in Files(root.Value)) streams.Add(path.Substring(root.Value.Length + 1).Replace('\\', '/'), new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read));
            }
            if (Directory.Exists(target)) {
                var existing = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(target, "export.json"), Encoding.UTF8));
                if (Convert.ToInt32(existing["format"]) != 1 || (string)existing["family"] != family || !(bool)existing["complete"]) throw new IOException("Vorhandene Sicherung passt nicht.");
                var sources = (Dictionary<string, object>)existing["sources"];
                foreach (var root in roots) {
                    var source = (Dictionary<string, object>)sources[root.Key];
                    if (!Equal((string)source["path"], root.Value)) throw new IOException("Sicherungspfad stimmt nicht.");
                    var expected = new Dictionary<string, string>();
                    foreach (var item in (Dictionary<string, object>)source["files"]) expected.Add(item.Key, (string)item.Value);
                    Same(expected, Inventory(root.Value)); Same(expected, Inventory(Path.Combine(target, root.Key)));
                }
                return;
            }
            string stage = Path.Combine(workspace, ".lohnmail-export-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(stage);
            var snapshots = new Dictionary<string, object>();
            foreach (var root in roots) {
                string copy = Path.Combine(stage, root.Key); Directory.CreateDirectory(copy);
                var hashes = new Dictionary<string, string>();
                foreach (var item in handles[root.Key]) {
                    string path = Path.Combine(copy, item.Key.Replace('/', '\\')); Directory.CreateDirectory(Path.GetDirectoryName(path));
                    hashes.Add(item.Key, Hash(item.Value)); item.Value.Position = 0;
                    using (FileStream output = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None)) { item.Value.CopyTo(output); output.Flush(true); }
                }
                Same(hashes, Inventory(copy)); Same(hashes, Inventory(root.Value));
                snapshots.Add(root.Key, new Dictionary<string, object> {{"path", root.Value}, {"files", hashes}});
            }
            foreach (var root in roots) Same((Dictionary<string,string>)((Dictionary<string,object>)snapshots[root.Key])["files"], Inventory(root.Value));
            WriteJson(Path.Combine(stage, "export.json"), new { format = 1, family = family, complete = true, identity_result = 15700, sources = snapshots });
            Directory.Move(stage, target);
        } finally { foreach (var source in handles.Values) foreach (var stream in source.Values) stream.Dispose(); }
    }

    [STAThread] static int Main(string[] args) {
        if (args.Length != 2) return 2;
        Dictionary<string, object> request = null;
        try {
            request = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(args[0], Encoding.UTF8));
            uint length = 0; int identity = GetCurrentPackageFamilyName(ref length, IntPtr.Zero);
            if (identity != 15700) {
                int depth = Int32.Parse(args[1]);
                if (depth >= 2) throw new IOException("Windows hat keinen unvervirtualisierten Sicherungsprozess gestartet.");
                return Breakaway(args[0], depth + 1);
            }
            Export(request);
            WriteJson((string)request["response"], new { complete = true, identity_result = identity });
            return 0;
        } catch (Exception error) {
            if (request != null) try { WriteJson((string)request["response"], new { complete = false, error = error.Message }); } catch { }
            return 1;
        }
    }
}
