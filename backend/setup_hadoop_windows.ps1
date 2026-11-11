# Run from PowerShell in your backend folder:
#   powershell -ExecutionPolicy Bypass -File .\setup_hadoop_windows.ps1
# Optional: pass your saved model folder to test the exact call that failed:
#   powershell -ExecutionPolicy Bypass -File .\setup_hadoop_windows.ps1 -ModelPath ".\data\saved_model\fire_predictor_spark_v1"
param([string]$ModelPath = "")

$ErrorActionPreference = "Stop"
$HadoopHome = "C:\hadoop"
$Bin = Join-Path $HadoopHome "bin"

Write-Host "`n== 1. Checking Python, Java, PySpark ==" -ForegroundColor Cyan
python --version
# java prints its version to stderr; run it via cmd so PowerShell does not treat that as an error
$javaLine = (cmd /c "java -version 2>&1" | Select-Object -First 1)
Write-Host "Java: $javaLine"

$jarsDir = python -c "import pyspark,os;print(os.path.join(os.path.dirname(pyspark.__file__),'jars'))"
$jar = Get-ChildItem $jarsDir -Filter "hadoop-client-api-*.jar" | Select-Object -First 1
$HadoopVersion = [regex]::Match($jar.Name, '\d+\.\d+\.\d+').Value
Write-Host "PySpark bundles Hadoop version: $HadoopVersion" -ForegroundColor Green

Write-Host "`n== 2. Installing compatible Python packages ==" -ForegroundColor Cyan
python -m pip install "pyarrow>=18" "pandas<3"

Write-Host "`n== 3. Preparing $Bin ==" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $Bin | Out-Null
$haveExe = Test-Path (Join-Path $Bin "winutils.exe")
$haveDll = Test-Path (Join-Path $Bin "hadoop.dll")

if (-not ($haveExe -and $haveDll)) {
    Write-Host "`nwinutils.exe and/or hadoop.dll are missing from $Bin." -ForegroundColor Yellow
    Write-Host @"

Download them manually (they must match your Hadoop version: $HadoopVersion):
  1. Open https://github.com/cdarlint/winutils
  2. Pick the folder closest to hadoop-$HadoopVersion (same major.minor, e.g. hadoop-3.3.x or 3.4.x)
  3. Copy everything from that folder's 'bin' into $Bin
     (at minimum winutils.exe and hadoop.dll)
  4. Run this script again.

These are community-built binaries, not official Apache files.
"@
    exit 1
}

Write-Host "Found winutils.exe and hadoop.dll." -ForegroundColor Green

Write-Host "`n== 4. Setting environment variables ==" -ForegroundColor Cyan
[Environment]::SetEnvironmentVariable("HADOOP_HOME", $HadoopHome, "User")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($null -eq $userPath) { $userPath = "" }
if ($userPath -notlike "*$Bin*") {
    [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(';') + ";" + $Bin), "User")
}
# also apply to the current session
$env:HADOOP_HOME = $HadoopHome
if ($env:Path -notlike "*$Bin*") { $env:Path = "$Bin;$env:Path" }
Write-Host "HADOOP_HOME = $env:HADOOP_HOME"

Write-Host "`n== 5. Testing Spark ==" -ForegroundColor Cyan
if ($ModelPath -ne "") { python check_spark.py $ModelPath } else { python check_spark.py }

Write-Host "`nDone. Open a NEW terminal / restart VS Code so the permanent variables apply." -ForegroundColor Cyan
