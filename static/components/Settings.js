const ComponentSettings = {
    props: ['config'],
    data() {
        return {
            formConfig: JSON.parse(JSON.stringify(this.config)),
            newFolder: '',
            isSubmitting: false
        }
    },
    template: `
    <div class="settings">
        <h2>系统配置</h2>
        <form @submit.prevent="saveConfig">
            <div class="settings-section">
                <h3>文件夹设置</h3>
                <div class="form-group">
                    <label>媒体文件夹</label>
                    <input type="text" v-model="formConfig.media_folder" required>
                    <button type="button" @click="browseFolder('media_folder')" class="browse-btn">浏览...</button>
                </div>

                <div class="form-group">
                    <label>输出文件夹</label>
                    <input type="text" v-model="formConfig.output_folder" required>
                    <button type="button" @click="browseFolder('output_folder')" class="browse-btn">浏览...</button>
                </div>

                <div class="form-group">
                    <label>临时片段文件夹</label>
                    <input type="text" v-model="formConfig.temp_segments_dir" required>
                    <button type="button" @click="browseFolder('temp_segments_dir')" class="browse-btn">浏览...</button>
                </div>
            </div>

            <div class="settings-section">
                <h3>ASR服务设置</h3>
                <div class="form-group checkbox">
                    <input type="checkbox" id="use_jianying_first" v-model="formConfig.use_jianying_first">
                    <label for="use_jianying_first">优先使用剪映识别</label>
                </div>
                <div class="form-group checkbox">
                    <input type="checkbox" id="use_kuaishou" v-model="formConfig.use_kuaishou">
                    <label for="use_kuaishou">启用快手识别</label>
                </div>
                <div class="form-group checkbox">
                    <input type="checkbox" id="use_bcut" v-model="formConfig.use_bcut">
                    <label for="use_bcut">启用必剪识别</label>
                </div>
            </div>

            <div class="settings-section">
                <h3>处理选项</h3>
                <div class="form-group checkbox">
                    <input type="checkbox" id="process_video" v-model="formConfig.process_video">
                    <label for="process_video">处理视频文件</label>
                </div>
                <div class="form-group checkbox">
                    <input type="checkbox" id="extract_audio_only" v-model="formConfig.extract_audio_only">
                    <label for="extract_audio_only">仅提取音频</label>
                </div>
                <div class="form-group checkbox">
                    <input type="checkbox" id="format_text" v-model="formConfig.format_text">
                    <label for="format_text">格式化文本</label>
                </div>
                <div class="form-group checkbox">
                    <input type="checkbox" id="include_timestamps" v-model="formConfig.include_timestamps">
                    <label for="include_timestamps">包含时间戳</label>
                </div>

                <div class="form-group">
                    <label>最大片段时长(分钟)</label>
                    <input type="number" v-model="formConfig.max_part_time" min="1" max="120" required>
                </div>

                <div class="form-group">
                    <label>日志级别</label>
                    <select v-model="formConfig.log_level">
                        <option value="VERBOSE">调试</option>
                        <option value="NORMAL">普通</option>
                        <option value="QUIET">最小</option>
                    </select>
                </div>
            </div>

            <div class="settings-section">
                <h3>监控设置</h3>
                <div class="form-group checkbox">
                    <input type="checkbox" id="monitoring_enabled" v-model="formConfig.enabled">
                    <label for="monitoring_enabled">启用文件夹监控</label>
                </div>

                <div v-if="formConfig.enabled">
                    <h4>额外监控文件夹</h4>
                    <div v-for="(folder, index) in formConfig.additional_folders" :key="index" class="folder-item">
                        <input type="text" v-model="formConfig.additional_folders[index]" readonly>
                        <button type="button" @click="removeFolder(index)" class="remove-btn">删除</button>
                    </div>

                    <div class="form-group">
                        <input type="text" v-model="newFolder" placeholder="添加新的监控文件夹">
                        <button type="button" @click="browseAdditionalFolder()" class="browse-btn">浏览...</button>
                        <button type="button" @click="addFolder()" class="add-btn" :disabled="!newFolder">添加</button>
                    </div>
                </div>
            </div>

            <div class="form-actions">
                <button type="submit" class="save-btn" :disabled="isSubmitting">
                    {{ isSubmitting ? '保存中...' : '保存配置' }}
                </button>
            </div>
        </form>
    </div>
    `,
    watch: {
        config: {
            handler(newConfig) {
                this.formConfig = JSON.parse(JSON.stringify(newConfig));
            },
            deep: true
        }
    },
    methods: {
        saveConfig() {
            this.isSubmitting = true;
            this.$emit('save-config', this.formConfig);
            setTimeout(() => {
                this.isSubmitting = false;
            }, 1000);
        },
        browseFolder(field) {
            // 此处应发送请求到后端API，让其打开系统文件选择对话框
            axios.get('/api/browse-folder')
                .then(response => {
                    if (response.data.path) {
                        this.formConfig[field] = response.data.path;
                    }
                })
                .catch(error => {
                    console.error('浏览文件夹失败:', error);
                });
        },
        browseAdditionalFolder() {
            axios.get('/api/browse-folder')
                .then(response => {
                    if (response.data.path) {
                        this.newFolder = response.data.path;
                    }
                })
                .catch(error => {
                    console.error('浏览文件夹失败:', error);
                });
        },
        addFolder() {
            if (this.newFolder && !this.formConfig.additional_folders.includes(this.newFolder)) {
                if (!this.formConfig.additional_folders) {
                    this.formConfig.additional_folders = [];
                }
                this.formConfig.additional_folders.push(this.newFolder);
                this.newFolder = '';
            }
        },
        removeFolder(index) {
            this.formConfig.additional_folders.splice(index, 1);
        }
    },
    emits: ['save-config']
};