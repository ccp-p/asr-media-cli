const ComponentFiles = {
    props: ['processedFiles'],
    data() {
        return {
            sortField: 'date',
            sortDirection: 'desc',
            searchQuery: '',
            filter: 'all' // 可选值: all, audio, video
        }
    },
    computed: {
        filteredAndSortedFiles() {
            // 先按搜索和类型过滤
            let result = this.processedFiles.filter(file => {
                // 搜索过滤
                const matchesSearch = file.filename.toLowerCase().includes(this.searchQuery.toLowerCase());
                // 类型过滤
                const matchesType = this.filter === 'all' || 
                                   (this.filter === 'audio' && this.isAudioFile(file.filename)) ||
                                   (this.filter === 'video' && this.isVideoFile(file.filename));
                
                return matchesSearch && matchesType;
            });
            
            // 然后排序
            result.sort((a, b) => {
                let comparison = 0;
                
                if (this.sortField === 'date') {
                    comparison = new Date(a.last_processed_time) - new Date(b.last_processed_time);
                } else if (this.sortField === 'name') {
                    comparison = a.filename.localeCompare(b.filename);
                } else if (this.sortField === 'parts') {
                    comparison = a.parts - b.parts;
                }
                
                return this.sortDirection === 'asc' ? comparison : -comparison;
            });
            
            return result;
        }
    },
    methods: {
        setSorting(field) {
            if (this.sortField === field) {
                // 如果已经在按这个字段排序，就切换排序方向
                this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                // 否则更换排序字段，并默认为降序
                this.sortField = field;
                this.sortDirection = 'desc';
            }
        },
        formatDate(dateString) {
            if (!dateString || dateString === "未知") return "未知";
            try {
                const date = new Date(dateString);
                return date.toLocaleString('zh-CN');
            } catch (e) {
                return dateString;
            }
        },
        isAudioFile(filename) {
            const audioExtensions = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'];
            return audioExtensions.some(ext => filename.toLowerCase().endsWith(ext));
        },
        isVideoFile(filename) {
            const videoExtensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'];
            return videoExtensions.some(ext => filename.toLowerCase().endsWith(ext));
        },
        getFileIcon(filename) {
            if (this.isAudioFile(filename)) {
                return '🎵'; // 音频文件图标
            } else if (this.isVideoFile(filename)) {
                return '🎬'; // 视频文件图标
            } else {
                return '📄'; // 默认文件图标
            }
        },
        reprocessFile(filepath) {
            this.$emit('process-file', filepath);
        },
        getProgressPercentage(file) {
            if (file.status === "完成") return 100;
            if (!file.parts || !file.total_parts) return 0;
            return Math.round((file.parts / file.total_parts) * 100);
        }
    },
    template: `
    <div class="files-container">
        <h2>已处理文件</h2>
        
        <div class="files-controls">
            <div class="search-bar">
                <input type="text" v-model="searchQuery" placeholder="搜索文件...">
            </div>
            <div class="filter-options">
                <select v-model="filter">
                    <option value="all">全部文件</option>
                    <option value="audio">仅音频</option>
                    <option value="video">仅视频</option>
                </select>
            </div>
        </div>
        
        <div class="files-list" v-if="filteredAndSortedFiles.length > 0">
            <table>
                <thead>
                    <tr>
                        <th>类型</th>
                        <th @click="setSorting('name')" class="sortable">
                            文件名
                            <span v-if="sortField === 'name'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
                        </th>
                        <th @click="setSorting('date')" class="sortable">
                            处理时间
                            <span v-if="sortField === 'date'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
                        </th>
                        <th>状态</th>
                        <th @click="setSorting('parts')" class="sortable">
                            片段
                            <span v-if="sortField === 'parts'">{{ sortDirection === 'asc' ? '▲' : '▼' }}</span>
                        </th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="file in filteredAndSortedFiles" :key="file.filepath">
                        <td>{{ getFileIcon(file.filename) }}</td>
                        <td>{{ file.filename }}</td>
                        <td>{{ formatDate(file.last_processed_time) }}</td>
                        <td>
                            <div class="progress">
                                <div class="progress-bar" :style="{ width: getProgressPercentage(file) + '%' }"></div>
                                <span class="progress-text">{{ file.status }}</span>
                            </div>
                        </td>
                        <td>{{ file.parts }}/{{ file.total_parts }}</td>
                        <td class="actions">
                            <button @click="reprocessFile(file.filepath)" title="重新处理">🔄</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div v-else class="no-files">
            <p>暂无处理过的文件</p>
        </div>
    </div>
    `,
    emits: ['process-file']
};