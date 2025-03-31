const app = Vue.createApp({
    data() {
        return {
            currentView: 'dashboard',
            config: {
                media_folder: '',
                output_folder: '',
                temp_segments_dir: '',
                use_jianying_first: false,
                use_kuaishou: true,
                use_bcut: true,
                process_video: true,
                extract_audio_only: false,
                format_text: true,
                include_timestamps: true,
                max_part_time: 20,
                log_level: 'NORMAL',
                enabled: false,
                additional_folders: []
            },
            stats: {},
            processedFiles: [],
            monitoringStatus: false
        }
    },
    created() {
        this.fetchConfig();
        this.fetchStats();
        this.fetchProcessedFiles();
        
        // 定期刷新数据
        setInterval(() => {
            this.fetchStats();
            this.fetchProcessedFiles();
        }, 30000); // 每30秒刷新一次
    },
    methods: {
        fetchConfig() {
            axios.get('/api/config')
                .then(response => {
                    this.config = response.data;
                    this.monitoringStatus = this.config.watch;
                })
                .catch(error => {
                    console.error('获取配置失败:', error);
                    alert('获取配置失败，请检查服务是否正常运行');
                });
        },
        fetchStats() {
            axios.get('/api/asr-stats')
                .then(response => {
                    this.stats = response.data;
                })
                .catch(error => {
                    console.error('获取统计信息失败:', error);
                });
        },
        fetchProcessedFiles() {
            axios.get('/api/processed-files')
                .then(response => {
                    this.processedFiles = response.data;
                })
                .catch(error => {
                    console.error('获取已处理文件列表失败:', error);
                });
        },
        saveConfig(newConfig) {
            axios.post('/api/config', newConfig)
                .then(() => {
                    this.config = newConfig;
                    alert('配置保存成功');
                })
                .catch(error => {
                    console.error('保存配置失败:', error);
                    alert('保存配置失败');
                });
        },
        processFile(filepath) {
            axios.post('/api/start-processing', { filepath })
                .then(response => {
                    alert('开始处理文件：' + filepath);
                })
                .catch(error => {
                    console.error('启动文件处理失败:', error);
                    alert('启动文件处理失败：' + (error.response?.data?.message || error.message));
                });
        },
        toggleMonitor(action) {
            axios.post('/api/toggle-monitor', { action })
                .then(response => {
                    this.monitoringStatus = action === 'start';
                    alert(action === 'start' ? '监控已启动' : '监控已停止');
                })
                .catch(error => {
                    console.error('切换监控状态失败:', error);
                    alert('切换监控状态失败');
                });
        }
    }
});

// 注册组件
app.component('component-dashboard', ComponentDashboard);
app.component('component-settings', ComponentSettings);
app.component('component-files', ComponentFiles);
app.component('component-logs', ComponentLogs);

// 挂载应用
app.mount('#app');