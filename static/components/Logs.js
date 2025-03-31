const ComponentLogs = {
    data() {
        return {
            logs: [],
            autoScroll: true,
            logLevel: 'all', // 可选值: all, info, warning, error
            searchQuery: '',
            isLoading: false,
            logUpdateInterval: null
        }
    },
    computed: {
        filteredLogs() {
            return this.logs.filter(log => {
                // 根据日志级别筛选
                const matchesLevel = this.logLevel === 'all' || 
                                    log.level.toLowerCase() === this.logLevel;
                                    
                // 根据搜索词筛选
                const matchesSearch = log.message.toLowerCase().includes(this.searchQuery.toLowerCase());
                
                return matchesLevel && matchesSearch;
            });
        }
    },
    created() {
        this.fetchLogs();
        // 设置定时获取日志的间隔
        this.logUpdateInterval = setInterval(() => {
            this.fetchLogs();
        }, 5000); // 每5秒更新一次日志
    },
    beforeUnmount() {
        // 组件卸载前清除定时器
        if (this.logUpdateInterval) {
            clearInterval(this.logUpdateInterval);
        }
    },
    updated() {
        // 如果启用了自动滚动，则滚动到底部
        if (this.autoScroll) {
            this.$nextTick(() => {
                const logContainer = this.$refs.logContainer;
                if (logContainer) {
                    logContainer.scrollTop = logContainer.scrollHeight;
                }
            });
        }
    },
    methods: {
        fetchLogs() {
            this.isLoading = true;
            axios.get('/api/logs')
                .then(response => {
                    this.logs = response.data;
                })
                .catch(error => {
                    console.error('获取日志失败:', error);
                })
                .finally(() => {
                    this.isLoading = false;
                });
        },
        clearLogs() {
            if (confirm('确定要清除所有日志吗？这个操作不可撤销。')) {
                axios.post('/api/clear-logs')
                    .then(() => {
                        this.logs = [];
                        alert('日志已清除');
                    })
                    .catch(error => {
                        console.error('清除日志失败:', error);
                        alert('清除日志失败');
                    });
            }
        },
        refreshLogs() {
            this.fetchLogs();
        },
        formatTime(timestamp) {
            const date = new Date(timestamp * 1000);
            return date.toLocaleString('zh-CN');
        },
        getLogClass(level) {
            switch(level.toLowerCase()) {
                case 'error':
                    return 'log-error';
                case 'warning':
                    return 'log-warning';
                case 'info':
                    return 'log-info';
                case 'debug':
                    return 'log-debug';
                default:
                    return '';
            }
        }
    },
    template: `
    <div class="logs-container">
        <h2>系统日志</h2>
        
        <div class="logs-controls">
            <div class="search-bar">
                <input type="text" v-model="searchQuery" placeholder="搜索日志...">
            </div>
            <div class="filter-options">
                <select v-model="logLevel">
                    <option value="all">全部日志</option>
                    <option value="info">信息</option>
                    <option value="warning">警告</option>
                    <option value="error">错误</option>
                    <option value="debug">调试</option>
                </select>
            </div>
            <div class="logs-actions">
                <label>
                    <input type="checkbox" v-model="autoScroll"> 自动滚动
                </label>
                <button @click="refreshLogs()" title="刷新日志" :disabled="isLoading">
                    <span v-if="isLoading">刷新中...</span>
                    <span v-else>刷新</span>
                </button>
                <button @click="clearLogs()" class="danger-btn" title="清除所有日志">清除日志</button>
            </div>
        </div>
        
        <div class="logs-list" ref="logContainer">
            <div v-if="filteredLogs.length > 0">
                <div v-for="(log, index) in filteredLogs" :key="index" :class="['log-entry', getLogClass(log.level)]">
                    <div class="log-header">
                        <span class="log-time">{{ formatTime(log.timestamp) }}</span>
                        <span class="log-level">{{ log.level.toUpperCase() }}</span>
                    </div>
                    <div class="log-message">{{ log.message }}</div>
                </div>
            </div>
            <div v-else class="no-logs">
                <p>暂无日志记录</p>
            </div>
        </div>
    </div>
    `
};