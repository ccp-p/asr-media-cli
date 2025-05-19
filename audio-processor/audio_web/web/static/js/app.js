document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const startUpload = document.getElementById('start-upload');
    const cancelUpload = document.getElementById('cancel-upload');
    const progressContainer = document.getElementById('progress-container');
    const progressBarInner = document.getElementById('progress-bar-inner');
    const statusMessage = document.getElementById('status-message');
    const resultContainer = document.getElementById('result-container');
    const segmentsContainer = document.getElementById('segments-container');
    const copyAllButton = document.getElementById('copy-all');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const tryAgainButton = document.getElementById('try-again');
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');

    // 当前选择的文件
    let selectedFile = null;
    let xhr = null;
    
    // 拖放文件相关事件
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.classList.remove('highlight');
    }
    
    // 处理文件拖放
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            handleFiles(files);
        }
    }
    
    // 文件输入框change事件
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFiles(this.files);
        }
    });
    
    // 处理选择的文件
    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            
            // 检查文件类型
            const validTypes = ['.mp3', '.wav', '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4a'];
            const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            
            if (!validTypes.some(type => fileExtension.endsWith(type))) {
                showError('不支持的文件类型，请选择音频或视频文件');
                return;
            }
            
            // 检查文件大小（限制为500MB）
            if (file.size > 500 * 1024 * 1024) {
                showError('文件过大，请选择小于500MB的文件');
                return;
            }
            
            selectedFile = file;
            fileName.textContent = formatFileName(selectedFile.name) + ' (' + formatFileSize(selectedFile.size) + ')';
            
            fileInfo.classList.remove('hidden');
            errorContainer.classList.add('hidden');
        }
    }
    
    function formatFileName(name) {
        if (name.length > 30) {
            return name.substring(0, 15) + '...' + name.substring(name.length - 12);
        }
        return name;
    }
    
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        else return (bytes / 1048576).toFixed(1) + ' MB';
    }
    
    // 上传文件
    startUpload.addEventListener('click', function() {
        if (!selectedFile) {
            showError('请先选择一个文件');
            return;
        }
        
        // 隐藏文件信息，显示进度
        fileInfo.classList.add('hidden');
        progressContainer.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        
        // 准备表单数据
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        // 创建XMLHttpRequest对象
        xhr = new XMLHttpRequest();
        
        // 进度监听
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressBarInner.style.width = percentComplete + '%';
                statusMessage.textContent = '正在上传文件... ' + Math.round(percentComplete) + '%';
            }
        });
        
        // 上传完成
        xhr.upload.addEventListener('load', function() {
            progressBarInner.style.width = '100%';
            statusMessage.textContent = '文件已上传，正在分析处理...';
        });
        
        // 处理结果
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            displayResult(response);
                        } else {
                            showError(response.error_message || '处理失败，请重试');
                        }
                    } catch (e) {
                        showError('解析响应失败: ' + e.message);
                    }
                } else if (xhr.status === 0) {
                    // 请求被中止，不显示错误
                    console.log('请求已取消');
                } else {
                    showError('请求失败: ' + xhr.status + ' ' + xhr.statusText);
                }
            }
        };
        
        // 错误处理
        xhr.addEventListener('error', function() {
            showError('网络错误，请检查网络连接后重试');
        });
        
        // 超时处理
        xhr.addEventListener('timeout', function() {
            showError('请求超时，服务器处理时间过长');
        });
        
        // 发送请求
        xhr.open('POST', '/upload', true);
        xhr.timeout = 600000; // 10分钟超时
        xhr.send(formData);
    });
    
    // 取消上传
    cancelUpload.addEventListener('click', function() {
        if (xhr && xhr.readyState < 4) {
            xhr.abort();
        }
        resetForm();
    });
    
    // 显示结果
    function displayResult(response) {
        progressContainer.classList.add('hidden');
        resultContainer.classList.remove('hidden');
        
        // 清空之前的结果
        segmentsContainer.innerHTML = '';
        
        // 处理识别结果
        debugger
        if (response.segments && response.segments.length > 0) {
            // 创建片段元素并添加到容器
            response.segments.forEach((segment, index) => {
                if (segment.text && segment.text.trim()) {
                    const segmentElement = document.createElement('div');
                    segmentElement.classList.add('text-segment');
                    segmentElement.textContent = segment.text.trim();
                    segmentsContainer.appendChild(segmentElement);
                }
            });
        } else {
            segmentsContainer.innerHTML = '<div class="text-segment">未检测到语音内容或文本为空</div>';
        }
        
        // 滚动到结果区域
        resultContainer.scrollIntoView({ behavior: 'smooth' });
    }
    
    // 显示错误
    function showError(message) {
        progressContainer.classList.add('hidden');
        resultContainer.classList.add('hidden');
        errorContainer.classList.remove('hidden');
        errorMessage.textContent = message;
        
        // 滚动到错误区域
        errorContainer.scrollIntoView({ behavior: 'smooth' });
    }
    
    // 显示提示消息
    function showToast(message) {
        toastMessage.textContent = message;
        toast.classList.remove('hidden');
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hidden');
        }, 3000);
    }
    
    // 复制全部文本
    copyAllButton.addEventListener('click', function() {
        // 收集所有段落文本
        let fullText = '';
        const segments = segmentsContainer.querySelectorAll('.text-segment');
        
        segments.forEach((segment, index) => {
            fullText += segment.textContent;
            if (index < segments.length - 1) {
                fullText += '\n\n';
            }
        });
        
        // 复制到剪贴板
        navigator.clipboard.writeText(fullText)
            .then(() => {
                showToast('文本已复制到剪贴板');
            })
            .catch(err => {
                console.error('复制失败: ', err);
                showToast('复制失败，请手动复制');
            });
    });
    
    // 重试
    tryAgainButton.addEventListener('click', function() {
        resetForm();
        // 滚动到顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    
    // 重置表单
    function resetForm() {
        fileInput.value = '';
        selectedFile = null;
        fileInfo.classList.add('hidden');
        progressContainer.classList.add('hidden');
        resultContainer.classList.add('hidden');
        errorContainer.classList.add('hidden');
        progressBarInner.style.width = '0%';
    }
});