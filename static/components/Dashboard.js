const ComponentDashboard = {
    props: ['stats', 'monitoringStatus'],
    template: `
    <div class="dashboard">
        <h2>仪表盘</h2>
        <div class="status-card">
            <h3>系统状态</h3>
            <div class="status-item">
                <span>文件监控：</span>
                <span :class="monitoringStatus ? 'status-active' : 'status-inactive'">
                    {{ monitoringStatus ? '运行中' : '已停止' }}
                </span>
                <button @click="$emit('toggle-monitor', monitoringStatus ? 'stop' : 'start')" class="action-btn">
                    {{ monitoringStatus ? '停止' : '启动' }}
                </button>
            </div>
        </div>

        <div class="stats-cards">
            <div class="stats-card">
                <h3>ASR服务统计</h3>
                <div v-if="stats && stats.services">
                    <div class="stat-row" v-for="(status, service) in stats.services" :key="service">
                        <span class="stat-label">{{ service }}:</span>
                        <span :class="status.available ? 'stat-value-success' : 'stat-value-error'">
                            {{ status.available ? '可用' : '不可用' }}
                        </span>
                    </div>
                </div>
                <div v-else class="no-stats">暂无服务统计数据</div>
            </div>

            <div class="stats-card">
                <h3>处理统计</h3>
                <div v-if="stats && stats.usage">
                    <div class="stat-row">
                        <span class="stat-label">已处理文件数:</span>
                        <span class="stat-value">{{ stats.usage.total_files || 0 }}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">已处理总时长:</span>
                        <span class="stat-value">{{ formatDuration(stats.usage.total_duration || 0) }}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">平均处理时间:</span>
                        <span class="stat-value">{{ stats.usage.avg_process_time ? formatDuration(stats.usage.avg_process_time) : '无数据' }}</span>
                    </div>
                </div>
                <div v-else class="no-stats">暂无处理统计数据</div>
            </div>
        </div>
    </div>
    `,
    methods: {
        formatDuration(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const remainingSeconds = Math.floor(seconds % 60);
            
            return `${hours}小时${minutes}分${remainingSeconds}秒`;
        }
    },
    emits: ['toggle-monitor']
};