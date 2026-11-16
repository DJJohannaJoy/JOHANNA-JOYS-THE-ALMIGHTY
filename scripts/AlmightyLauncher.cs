using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
[assembly: AssemblyTitle("JOHANNA JOY'S THE ALMIGHTY")]
[assembly: AssemblyProduct("JOHANNA JOY'S THE ALMIGHTY")]
[assembly: AssemblyVersion("1.14.2.0")]
[assembly: AssemblyFileVersion("1.14.2.0")]
internal static class AlmightyLauncher {
    private static readonly object LogLock = new object();
    private static void Record(string path,string message) {
        lock(LogLock) File.AppendAllText(path,message,Encoding.UTF8);
    }
    private static string Quote(string value) { return "\"" + value.Replace("\"", "\\\"") + "\""; }
    [STAThread] private static int Main(string[] args) {
        bool check = args.Length == 2 && args[0] == "--self-test";
        try {
            string home = AppDomain.CurrentDomain.BaseDirectory;
            string app = Path.Combine(home,"APP"), runtime = Path.Combine(home,"runtime");
            string python = Path.Combine(runtime,"python.exe");
            if (!File.Exists(python)) throw new Exception("Bitte das gesamte ZIP entpacken. APP und runtime müssen neben der Programm-EXE bleiben.");
            string data = Environment.GetEnvironmentVariable("ALMIGHTY_DATA_ROOT");
            if (String.IsNullOrEmpty(data)) {
                data = Path.Combine(home,"Daten");
            }
            string logs = Path.Combine(data,"Protokolle");Directory.CreateDirectory(logs);
            string log = Path.Combine(logs,"PROGRAMM_START.txt");
            Record(log,Environment.NewLine+"["+DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")+"] Start: "+python+Environment.NewLine);
            ProcessStartInfo info = new ProcessStartInfo(python);
            info.WorkingDirectory = app;info.UseShellExecute = false;info.CreateNoWindow = true;
            info.Arguments = "-X faulthandler -X utf8 " + Quote(Path.Combine(app,check ? "verify_installation.py" : "almighty.py"));
            if (check) info.Arguments += " " + Quote(Path.GetFullPath(args[1]));
            info.EnvironmentVariables.Remove("PYTHONPATH");info.EnvironmentVariables.Remove("PYTHONHOME");
            info.EnvironmentVariables["PYTHONNOUSERSITE"]="1";
            info.EnvironmentVariables["PYTHONFAULTHANDLER"]="1";
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
                    if (e.Data!=null) Record(log,e.Data+Environment.NewLine);
                };
                process.ErrorDataReceived+=record;process.OutputDataReceived+=record;
                process.Start();process.BeginErrorReadLine();process.BeginOutputReadLine();process.WaitForExit();
                Record(log,"["+DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")+"] Exit: "+process.ExitCode+" (0x"+unchecked((uint)process.ExitCode).ToString("X8")+")"+Environment.NewLine);
                if(process.ExitCode!=0 && !check) MessageBox.Show("Das Programm wurde mit einem Fehler beendet. Details: "+log,"JOHANNA JOY'S THE ALMIGHTY",MessageBoxButtons.OK,MessageBoxIcon.Error);
                return process.ExitCode;
            }
        } catch(Exception e) {
            if(!check) MessageBox.Show(e.Message,"JOHANNA JOY'S THE ALMIGHTY",MessageBoxButtons.OK,MessageBoxIcon.Error);
            return 1;
        }
    }
}
