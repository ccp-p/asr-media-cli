obj.get_video_title = function() {
    // 查找包含"filename"的类名元素
    console.log("开始查找文件名元素...");
    function findFilenameElement() {
        const allElements = document.querySelectorAll('*');
        let filenameElement = null;
        
        for (const element of allElements) {
            if (element.className && typeof element.className === 'string' && 
                element.className.toLowerCase().includes('filename')) {
                console.log("找到filename元素:", element);
                filenameElement = element;
                break;
            }
        }
        
        return filenameElement;
    }
    
    // 显示通知和文件名
    function showFilenameBox(text) {
        // 移除之前的通知框(如果有)
        const oldBox = document.getElementById('filename-extraction-box');
        if (oldBox) {
            oldBox.remove();
        }
        
        // 创建一个漂浮的通知框
        const box = document.createElement('div');
        box.id = 'filename-extraction-box';
        box.style.position = 'fixed';
        box.style.top = '20px';
        box.style.left = '50%';
        box.style.transform = 'translateX(-50%)';
        box.style.backgroundColor = '#f8f9fa';
        box.style.border = '1px solid #ccc';
        box.style.padding = '15px';
        box.style.borderRadius = '5px';
        box.style.zIndex = '9999';
        box.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
        box.style.minWidth = '300px';
        box.style.textAlign = 'center';
        
        // 添加标题
        const title = document.createElement('div');
        title.textContent = '提取到的文件名';
        title.style.fontWeight = 'bold';
        title.style.marginBottom = '10px';
        box.appendChild(title);
        
        // 添加文件名文本框
        const textBox = document.createElement('input');
        textBox.type = 'text';
        textBox.value = text;
        textBox.style.width = '90%';
        textBox.style.padding = '5px';
        textBox.style.marginBottom = '10px';
        textBox.style.borderRadius = '3px';
        textBox.style.border = '1px solid #ddd';
        box.appendChild(textBox);
        
        // 添加复制按钮
        const copyBtn = document.createElement('button');
        copyBtn.textContent = '复制文件名';
        copyBtn.style.padding = '5px 10px';
        copyBtn.style.backgroundColor = '#4CAF50';
        copyBtn.style.color = 'white';
        copyBtn.style.border = 'none';
        copyBtn.style.borderRadius = '3px';
        copyBtn.style.cursor = 'pointer';
        copyBtn.style.marginRight = '10px';
        copyBtn.onclick = function() {
            textBox.select();
            document.execCommand('copy');
            copyBtn.textContent = '已复制!';
            setTimeout(() => { copyBtn.textContent = '复制文件名'; }, 2000);
        };
        box.appendChild(copyBtn);
        
        // 添加关闭按钮
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '关闭';
        closeBtn.style.padding = '5px 10px';
        closeBtn.style.backgroundColor = '#f44336';
        closeBtn.style.color = 'white';
        closeBtn.style.border = 'none';
        closeBtn.style.borderRadius = '3px';
        closeBtn.style.cursor = 'pointer';
        closeBtn.onclick = function() {
            box.remove();
        };
        box.appendChild(closeBtn);
        
        // 可拖动功能
        let isDragging = false;
        let offsetX, offsetY;
        
        title.style.cursor = 'move';
        title.onmousedown = function(e) {
            isDragging = true;
            offsetX = e.clientX - box.getBoundingClientRect().left;
            offsetY = e.clientY - box.getBoundingClientRect().top;
        };
        
        document.addEventListener('mousemove', function(e) {
            if (isDragging) {
                box.style.left = (e.clientX - offsetX) + 'px';
                box.style.top = (e.clientY - offsetY) + 'px';
                box.style.transform = 'none'; // 移除居中效果
            }
        });
        
        document.addEventListener('mouseup', function() {
            isDragging = false;
        });
        
        // 添加到页面
        document.body.appendChild(box);
        
        // 自动选中文本以便复制
        textBox.select();
    }
    
    // 主函数：查找文件名并显示
    function findAndShowFilename() {
        const element = findFilenameElement();
        
        if (element) {
            // 清理文本（移除多余空格和不允许的文件名字符）
            let text = element.textContent.trim().replace(/[\r\n\t]+/g, ' ');
            text = text.replace(/[\\/:*?"<>|]/g, '_');
            text = `D:\\download\\${text}`;
            console.log('找到文件名:', text);
            const isEndWithMp4 = text.endsWith('.mp4');
            // change suffix to ts 
            if (isEndWithMp4) {
                text = text.replace(/\.mp4$/, '.ts');
            }
            showFilenameBox(text);
            copyToClipboard(text); // 复制到剪贴板
        } else {
            console.error('未找到包含filename的类名元素');
            showFilenameBox('未找到文件名，请手动输入');
        }
    }
    
    // 设置快捷键 Alt+T
    document.addEventListener('keydown', function(e) {
        if (e.altKey && e.key === 't') {
            findAndShowFilename();
        }
    });
    
    // 立即执行一次查找
    findAndShowFilename();
    
    copyToClipboard = function(text) {
        console.log("复制到剪贴板:", text);
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
    };
    // 返回设置了快捷键的信息
    return "已设置Alt+T快捷键用于获取文件名，并立即显示文件名对话框";
}