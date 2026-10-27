# 스타게이트 블로그 TWA AAB 빌드 스크립트 (Windows PowerShell)
# 패키지: kr.co.stargateedu.blog / 호스트: blog.stargateedu.co.kr
#
# 사용법 (PowerShell):
#   Set-ExecutionPolicy -Scope Process Bypass
#   & "<이 파일 경로>"
#
# 결과물: 작업 폴더의 app-release-bundle.aab (Play Console 업로드용)
# 주의: 업로드 키스토어(stargate-blog-upload.keystore)와 비밀번호는 분실하지 마십시오.
#       GitHub 등 외부 저장소에 올리지 않습니다.

$ErrorActionPreference = 'Stop'
$WorkDir  = Join-Path $env:USERPROFILE 'Desktop\Cowork(260323)\스타게이트블로그_앱'
$Manifest = 'https://raw.githubusercontent.com/DongsooJung/stargate-blog-hub/main/android/twa-manifest.json'
$Keystore = Join-Path $WorkDir 'stargate-blog-upload.keystore'
$Alias    = 'upload'

Write-Host '[1/6] 작업 폴더 준비' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
Set-Location $WorkDir
if (-not (Test-Path 'twa-manifest.json')) {
    Invoke-WebRequest -Uri $Manifest -OutFile 'twa-manifest.json' -UseBasicParsing
}

Write-Host '[2/6] Node.js / Bubblewrap 확인' -ForegroundColor Cyan
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js가 필요합니다. https://nodejs.org 에서 LTS를 설치하십시오.' }
if (-not (Get-Command bubblewrap -ErrorAction SilentlyContinue)) { npm install -g @bubblewrap/cli }

Write-Host '[3/6] JDK / Android SDK 확인 (최초 1회: 설치 질문에 모두 Y로 답하십시오)' -ForegroundColor Cyan
bubblewrap doctor
if ($LASTEXITCODE -ne 0) { bubblewrap doctor }

$Keytool = Get-ChildItem (Join-Path $env:USERPROFILE '.bubblewrap') -Recurse -Filter keytool.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $Keytool) { throw 'keytool.exe를 찾지 못했습니다. bubblewrap doctor로 JDK 설치를 먼저 완료하십시오.' }

Write-Host '[4/6] 비밀번호 입력' -ForegroundColor Cyan
$sec = Read-Host '키스토어 비밀번호 (신규 생성 시 6자 이상, 반드시 별도 보관)' -AsSecureString
$pw  = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$env:BUBBLEWRAP_KEYSTORE_PASSWORD = $pw
$env:BUBBLEWRAP_KEY_PASSWORD      = $pw

if (-not (Test-Path $Keystore)) {
    Write-Host '      업로드 키스토어 신규 생성' -ForegroundColor Yellow
    & $Keytool -genkeypair -v -keystore $Keystore -alias $Alias -keyalg RSA -keysize 2048 -validity 10000 `
        -storepass $pw -keypass $pw `
        -dname 'CN=STARGATE EDU, OU=Mobile, O=Byeoluimun Inc., L=Seoul, ST=Seoul, C=KR'
}

Write-Host '[5/6] 프로젝트 생성 및 빌드' -ForegroundColor Cyan
bubblewrap update --skipVersionUpgrade
bubblewrap build --skipPwaValidation

Write-Host '[6/6] 업로드 키 SHA-256 지문' -ForegroundColor Cyan
$out = & $Keytool -list -v -keystore $Keystore -alias $Alias -storepass $pw
$sha = ($out | Select-String 'SHA256:').ToString().Split(':',2)[1].Trim()
$sha | Out-File -Encoding utf8 (Join-Path $WorkDir '업로드키_SHA256.txt')
Remove-Item Env:BUBBLEWRAP_KEYSTORE_PASSWORD, Env:BUBBLEWRAP_KEY_PASSWORD

Write-Host ''
Write-Host "완료: $(Join-Path $WorkDir 'app-release-bundle.aab')" -ForegroundColor Green
Write-Host "업로드 키 SHA-256: $sha" -ForegroundColor Green
Write-Host '다음 단계: Play Console에 AAB 업로드 → [앱 무결성]의 "앱 서명 키 인증서 SHA-256"과 위 지문을 assetlinks.json에 등록' -ForegroundColor Green
