# Configure current-user credentials without placing secrets in shell history.
# Run: powershell -ExecutionPolicy Bypass -File scripts\set_credentials.ps1
$ErrorActionPreference = 'Stop'
$appId = (Read-Host 'Baidu APPID').Trim()
if ([string]::IsNullOrWhiteSpace($appId)) { throw 'APPID is required.' }
$secure = Read-Host 'Baidu secret key (hidden)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $secret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    if ([string]::IsNullOrWhiteSpace($secret)) { throw 'Secret key is required.' }
    foreach ($name in @('BAIDU_APPID', 'BAIDU_SECRET_KEY')) {
        $existing = [Environment]::GetEnvironmentVariable($name, 'User')
        if (-not [string]::IsNullOrEmpty($existing)) {
            $answer = Read-Host "$name already exists. Replace it? Type YES to confirm"
            if ($answer -cne 'YES') { throw 'Cancelled. Existing credentials kept.' }
        }
    }
    [Environment]::SetEnvironmentVariable('BAIDU_APPID', $appId, 'User')
    [Environment]::SetEnvironmentVariable('BAIDU_SECRET_KEY', $secret, 'User')
    $env:BAIDU_APPID = $appId
    $env:BAIDU_SECRET_KEY = $secret
    Write-Output 'Saved to Windows user environment. Restart terminals and the application.'
    Write-Output 'No credentials were written into project files.'
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $secret = $null
    $secure.Dispose()
}
