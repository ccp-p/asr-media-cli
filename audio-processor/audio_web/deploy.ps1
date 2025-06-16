# 设置变量
$serverIp = "your-server-ip"
$username = "admin"
$remotePath = "/home/admin/audio-web"
$localPath = "D:\project\my_py_project\segement_audio\audio-processor\audio_web"

# 编译应用
Write-Host "正在为Linux编译应用..." -ForegroundColor Yellow
$env:GOOS = "linux"
$env:GOARCH = "amd64"
go build -o audio-web main.go

if ($LASTEXITCODE -ne 0) {
    Write-Host "编译失败！" -ForegroundColor Red
    exit
}

# 上传二进制文件
Write-Host "上传二进制文件到服务器..." -ForegroundColor Yellow
ssh $username@$serverIp "mkdir -p $remotePath"
scp "$localPath\audio-web" "$username@$serverIp:$remotePath/audio-web.new"

# 部署更新
Write-Host "部署更新..." -ForegroundColor Yellow
ssh $username@$serverIp "chmod +x $remotePath/audio-web.new && sudo systemctl stop audio-web && mv $remotePath/audio-web.new $remotePath/audio-web && sudo systemctl start audio-web"

# 检查服务状态
Write-Host "检查服务状态..." -ForegroundColor Yellow
ssh $username@$serverIp "sudo systemctl status audio-web"

Write-Host "部署完成！" -ForegroundColor Green