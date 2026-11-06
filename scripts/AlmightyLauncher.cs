using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
[assembly: AssemblyTitle("THE ALMIGHTY")]
[assembly: AssemblyProduct("Johanna Joy's THE ALMIGHTY")]
[assembly: AssemblyVersion("1.13.0.0")]
[assembly: AssemblyFileVersion("1.13.0.0")]
internal static class AlmightyLauncher {
    private static readonly object LogLock = new object();
    private static string Quote(string value) { return "\"" + value.Replace("\"", "\\\"") + "\""; }
    [STAThread] private static int Main(string[] args) {
        bool check = args.Length == 2 && args[0] == "--self-test";
        try {
            string home = AppDomain.CurrentDomain.BaseDirectory;
            string app = Path.Combine(home,"APP"), runtime = Path.Combine(home,"runtime");
            string python = Path.Combine(runtime,"python.exe");
            if (!File.Exists(python)) throw new Exception("Bitte das gesamte ZIP entpacken. Der Ordner runtime muss neben THE_ALMIGHTY.exe bleiben.");
            string data = Environment.GetEnvironmentVariable("ALMIGHTY_DATA_ROOT");
            if (String.IsNullOrEmpty(data)) {
                string prior = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"SET SCANNER");
                data = File.Exists(Path.Combine(prior,"einstellungen.json")) ? prior : app;
            }
            string logs = Path.Combine(data,"Protokolle");Directory.CreateDirectory(logs);
            string log = Path.Combine(logs,"PROGRAMM_START.txt");
            ProcessStartInfo info = new ProcessStartInfo(python);
            info.WorkingDirectory = app;info.UseShellExecute = false;info.CreateNoWindow = true;
            info.Arguments = "-X utf8 " + Quote(Path.Combine(app,check ? "portable_check.py" : "scanner.py"));
            if (check) info.Arguments += " " + Quote(Path.GetFullPath(args[1]));
            info.EnvironmentVariables.Remove("PYTHONPATH");info.EnvironmentVariables.Remove("PYTHONHOME");
            info.EnvironmentVariables["PYTHONNOUSERSITE"]="1";
            info.EnvironmentVariables["PYTHONUTF8"]="1";
            info.EnvironmentVariables["PYTHONIOENCODING"]="utf-8";
            info.EnvironmentVariables["ALMIGHTY_DATA_ROOT"]=data;
            info.EnvironmentVariables["TCL_LIBRARY"]=Path.Combine(runtime,"tcl","tcl8.6");
            info.EnvironmentVariables["TK_LIBRARY"]=Path.Combine(runtime,"tcl","tk8.6");
            info.EnvironmentVariables["PATH"]=Path.Combine(app,"tools","node")+";"+Path.Combine(app,"tools","ffmpeg")+";"+info.EnvironmentVariables["PATH"];
            info.RedirectStandardError=true;info.RedirectStandardOutput=true;
            using (Process process = new Process()) {
                process.StartInfo=info;
                DataReceivedEventHandler record = delegate(object sender,DataReceivedEventArgs e) {
                    if (e.Data!=null) lock(LogLock) File.AppendAllText(log,e.Data+Environment.NewLine,Encoding.UTF8);
                };
                process.ErrorDataReceived+=record;process.OutputDataReceived+=record;
                process.Start();process.BeginErrorReadLine();process.BeginOutputReadLine();process.WaitForExit();
                if(process.ExitCode!=0 && !check) MessageBox.Show("Das Programm wurde mit einem Fehler beendet. Details: "+log,"THE ALMIGHTY",MessageBoxButtons.OK,MessageBoxIcon.Error);
                return process.ExitCode;
            }
        } catch(Exception e) {
            if(!check) MessageBox.Show(e.Message,"THE ALMIGHTY",MessageBoxButtons.OK,MessageBoxIcon.Error);
            return 1;
        }
    }
}
