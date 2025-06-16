const { createApp } = Vue;

createApp({
    data() {
        return {
            // 视图控制
            currentView: 'upload', // upload, progress, result, error
            
            // 文件相关
            selectedFile: null,
            isDragging: false,
            
            // 进度相关
            progress: 0,
            statusMessage: '正在准备...',
            
            // 结果相关
            segments: [],
            transcriptionText: '',
            
            // 总结相关
            showSummary: false,
            summary: '',
            customPrompt: '',
            summaryLoading: false,
            summaryLoadingText: '正在生成摘要...',
            summaryError: null,
            lastPrompt: '',  // 记录上一次的提示词，用于重试
            
            // 提示相关
            toastVisible: false,
            toastMessage: '',
            
            // 错误相关
            errorMessage: '',
            
            // XHR 请求
            xhr: null
        }
    },
    
    computed: {
        formattedFileName() {
            if (!this.selectedFile) return '';
            const name = this.selectedFile.name;
            if (name.length > 30) {
                return name.substring(0, 15) + '...' + name.substring(name.length - 12);
            }
            return name;
        },
        
        formattedFileSize() {
            if (!this.selectedFile) return '';
            const bytes = this.selectedFile.size;
            if (bytes < 1024) return bytes + ' B';
            else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
            else return (bytes / 1048576).toFixed(1) + ' MB';
        },
        
        progressPercentage() {
            return this.progress;
        },
        
        hasTranscriptionContent() {
            return this.transcriptionText.trim().length > 0;
        }
    },
    
    methods: {
        // 文件处理相关
        handleDrop(e) {
            this.isDragging = false;
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                this.handleFiles(files);
            }
        },
        
        handleFileSelect(e) {
            if (e.target.files.length > 0) {
                this.handleFiles(e.target.files);
            }
        },
        
        handleFiles(files) {
            if (files.length > 0) {
                const file = files[0];
                
                // 检查文件类型
                const validTypes = ['.mp3', '.wav', '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4a'];
                const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
                
                if (!validTypes.some(type => fileExtension.endsWith(type))) {
                    this.showError('不支持的文件类型，请选择音频或视频文件');
                    return;
                }
                
                // 检查文件大小（限制为500MB）
                if (file.size > 500 * 1024 * 1024) {
                    this.showError('文件过大，请选择小于500MB的文件');
                    return;
                }
                
                this.selectedFile = file;
            }
        },
        
        // 上传处理
        startUpload() {
            if (!this.selectedFile) {
                this.showError('请先选择一个文件');
                return;
            }
            debugger
            // 切换到进度视图
            this.currentView = 'progress';
            this.progress = 0;
            this.statusMessage = '准备上传...';
            
            // 准备表单数据
            const formData = new FormData();
            formData.append('file', this.selectedFile);
            
            // 创建XMLHttpRequest对象
            this.xhr = new XMLHttpRequest();
            
            // 进度监听
            this.xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    this.progress = (e.loaded / e.total) * 100;
                    this.statusMessage = '正在上传文件... ' + Math.round(this.progress) + '%';
                }
            });
            
            // 上传完成
            this.xhr.upload.addEventListener('load', () => {
                this.progress = 100;
                this.statusMessage = '文件已上传，正在分析处理...';
            });
            
            // 处理结果
            this.xhr.onreadystatechange = () => {
                if (this.xhr.readyState === 4) {
                    if (this.xhr.status === 200) {
                        try {
                            const response = JSON.parse(this.xhr.responseText);
                            if (response.success) {
                                this.handleResponse(response);
                            } else {
                                this.showError(response.error_message || '处理失败，请重试');
                            }
                        } catch (e) {
                            this.showError('解析响应失败: ' + e.message);
                        }
                    } else if (this.xhr.status === 0) {
                        // 请求被中止，不显示错误
                        console.log('请求已取消');
                    } else {
                        this.showError('请求失败: ' + this.xhr.status + ' ' + this.xhr.statusText);
                    }
                }
            };
            
            // 错误处理
            this.xhr.addEventListener('error', () => {
                this.showError('网络错误，请检查网络连接后重试');
            });
            
            // 超时处理
            this.xhr.addEventListener('timeout', () => {
                this.showError('请求超时，服务器处理时间过长');
            });
            
            // 发送请求
            this.xhr.open('POST', '/upload', true);
            this.xhr.timeout = 600000; // 10分钟超时
            this.xhr.send(formData);
        },
        
        cancelUpload() {
            if (this.xhr && this.xhr.readyState < 4) {
                this.xhr.abort();
            }
            this.resetForm();
        },
        
        // 结果处理
        handleResponse(response) {
            // 保存段落数据
            this.segments = [];
            this.transcriptionText = '';
            
            if (response.segments && response.segments.length > 0) {
                this.segments = response.segments.filter(segment => 
                    segment.text && segment.text.trim()
                );
                
                // 构建完整文本
                this.transcriptionText = this.segments
                    .map(segment => segment.text.trim())
                    .join(' ');
            }
            
            // 切换到结果视图
            this.currentView = 'result';
            this.showSummary = false;
            
            // 滚动到顶部
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        
        // 总结相关
        generateSummary() {
            if (!this.hasTranscriptionContent) {
                this.showToast('没有足够的文本内容用于总结');
                return;
            }
            
            this.showSummary = true;
            this.summaryLoading = true;
            this.summaryLoadingText = '正在生成摘要...';
            this.summaryError = null;
            this.lastPrompt = '';
            
            // 滚动到总结部分
            this.$nextTick(() => {
                const summaryEl = document.querySelector('.summary-section');
                if (summaryEl) summaryEl.scrollIntoView({ behavior: 'smooth' });
            });
            
            // 发送请求
            this.fetchSummary(this.transcriptionText);
        },
        
        generateCustomSummary() {
            const customPrompt = this.customPrompt.trim();
            
            if (!this.hasTranscriptionContent) {
                this.showToast('没有足够的文本内容用于总结');
                return;
            }
            
            if (!customPrompt) {
                this.showToast('请输入自定义提示词');
                return;
            }
            
            this.showSummary = true;
            this.summaryLoading = true;
            this.summaryLoadingText = '正在根据提示生成...';
            this.summaryError = null;
            this.lastPrompt = customPrompt;
            
            // 滚动到总结部分
            this.$nextTick(() => {
                const summaryEl = document.querySelector('.summary-section');
                if (summaryEl) summaryEl.scrollIntoView({ behavior: 'smooth' });
            });
            
            // 发送请求
            this.fetchSummary(this.transcriptionText, customPrompt);
        },
        
        fetchSummary(text, customPrompt = '') {
            // 准备请求数据
            const requestData = {
                text: text
            };
            
            // 如果有自定义提示词，添加到请求中
            if (customPrompt) {
                requestData.prompt = customPrompt;
            }
            
            // 发送请求
            fetch('/api/summarize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('服务器响应错误: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                // 显示总结结果
                this.summaryLoading = false;
                if (data.summary) {
                    this.summary = data.summary;
                } else {
                    throw new Error('返回数据格式错误');
                }
            })
            .catch(error => {
                console.error('获取摘要失败:', error);
                this.summaryLoading = false;
                this.summaryError = error.message;
            });
        },
        
        retrySummary() {
            // 重试上一次的摘要生成
            this.summaryLoading = true;
            this.summaryLoadingText = this.lastPrompt ? '正在根据提示生成...' : '正在生成摘要...';
            this.summaryError = null;
            
            // 重新发送请求
            this.fetchSummary(this.transcriptionText, this.lastPrompt);
        },
        
        // 复制相关
        copyAllText() {
            if (!this.transcriptionText.trim()) {
                this.showToast('没有可复制的文本内容');
                return;
            }
            
            this.copyToClipboard(this.transcriptionText);
        },
        
        copySummary() {
            if (!this.summary.trim() || this.summaryLoading) {
                this.showToast('没有可复制的摘要内容');
                return;
            }
            
            this.copyToClipboard(this.summary);
        },
        
        copyToClipboard(text) {
            // 尝试使用现代剪贴板API
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text)
                    .then(() => {
                        this.showToast('文本已复制到剪贴板');
                    })
                    .catch(err => {
                        console.error('API复制失败，尝试备选方法: ', err);
                        this.fallbackCopy(text);
                    });
            } else {
                // 使用备选复制方法
                this.fallbackCopy(text);
            }
        },
        
        fallbackCopy(text) {
            // 创建临时文本区域
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';  // 避免滚动到底部
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            
            if (/iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
                // 移动设备
                textArea.style.top = '0';
                textArea.style.opacity = '1';  // 使字段可见以便于互动
                textArea.style.height = '58px';
                
                // 选中文本
                textArea.focus();
                textArea.select();
                
                // 显示特殊提示
                this.showToast('请长按选中文本并复制');
                
                // 10秒后移除文本区
                setTimeout(() => {
                    document.body.removeChild(textArea);
                }, 10000);
            } else {
                // 桌面设备
                textArea.select();
                
                try {
                    // 执行复制命令
                    const successful = document.execCommand('copy');
                    if (successful) {
                        this.showToast('文本已复制到剪贴板');
                    } else {
                        this.showToast('复制失败，请手动复制');
                    }
                } catch (err) {
                    console.error('execCommand复制失败: ', err);
                    this.showToast('复制失败，请手动复制');
                }
                
                // 移除临时元素
                document.body.removeChild(textArea);
            }
        },
        
        // 错误处理
        showError(message) {
            this.errorMessage = message;
            this.currentView = 'error';
        },
        
        tryAgain() {
            this.resetForm();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        
        // Toast提示
        showToast(message) {
            this.toastMessage = message;
            this.toastVisible = true;
            
            // 3秒后隐藏
            setTimeout(() => {
                this.toastVisible = false;
            }, 3000);
        },
        
        // 表单重置
        resetForm() {
            this.selectedFile = null;
            this.progress = 0;
            this.segments = [];
            this.showSummary = false;
            this.summary = '';
            this.customPrompt = '';
            this.transcriptionText = '';
            this.currentView = 'upload';
            
            // 重置文件输入
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.value = '';
        }
    }
}).mount('#app');