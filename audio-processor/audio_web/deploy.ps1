# filepath: d:\project\my_py_project\segement_audio\audio-processor\audio_web\deploy.ps1
chcp 65001 > $null

# 设置变量
$serverIp = "8.134.32.71" # 请替换为您的服务器IP
$username = "root"
$remotePath = "/home/admin/audio-web"
$localPath = "D:\project\my_py_project\segement_audio\audio-processor\audio_web"

# 编译应用
Write-Host "building..." -ForegroundColor Yellow
$env:GOOS = "linux"
$env:GOARCH = "amd64"
$env:CGO_ENABLED = "0"

go build -o audio-web main.go

if ($LASTEXITCODE -ne 0) { Write-Host "compile failed" } else { Write-Host "compile success" }


# 上传二进制文件
Write-Host "upload..." -ForegroundColor Yellow

ssh "$username@$serverIp" "mkdir -p $remotePath"

$scpSourcePath = "$localPath\audio-web"
$scpDestinationPath = "${username}@${serverIp}:${remotePath}/audio-web.new"

scp $scpSourcePath $scpDestinationPath

# 部署更新
Write-Host "deploying..." -ForegroundColor Yellow
ssh "$username@$serverIp" "chmod +x $remotePath/audio-web.new; sudo systemctl stop audio-web; mv $remotePath/audio-web.new $remotePath/audio-web; sudo systemctl start audio-web"

# 检查服务状态
Write-Host "check..." -ForegroundColor Yellow
ssh "$username@$serverIp" "sudo systemctl status audio-web"

Write-Host "deployment complete!" -ForegroundColor Green