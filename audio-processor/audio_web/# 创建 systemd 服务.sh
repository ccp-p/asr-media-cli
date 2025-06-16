# 创建 systemd 服务
sudo tee /etc/systemd/system/audio-web.service > /dev/null << EOF
[Unit]
Description=Audio Web Service
After=network.target

[Service]
User=admin
WorkingDirectory=/home/admin/audio-web
ExecStart=/home/admin/audio-web/audio-web --config=/home/admin/audio-web/configs/config.yaml --port=8080
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable audio-web
sudo systemctl start audio-web
sudo systemctl status audio-web