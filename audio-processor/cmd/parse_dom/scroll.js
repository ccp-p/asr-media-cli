let scrollContainerSelector = 'div.search-super-content-container.search-super-content-links'; // 要滚动的容器的选择器
// 面板
// scrollContainerSelector = 'div.bubble.channel-post'

let itemSelector = 'a.row.row-with-padding.row-clickable.hover-effect.search-super-item'; // 要统计的元素的选择器

// itemSelector = 'div.bubble-content'; // 要统计的元素的选择器

const scrollDelay = 100; // 每次滚动后等待的毫秒数
const checkInterval = 100; // setInterval 的间隔时间
// --- 配置结束 ---

let scrollIntervalId = null;
let isProcessing = false;
let lastItemCount = 0;
let noNewItemCount = 0;
let processedItemCount = 0; // 新增：跟踪已处理/发送的 item 数量

// 新增：发送新 item 数据到服务器的函数
function sendNewItemsToServer(newItems) {
    if (!newItems || newItems.length === 0) {
        console.log("[发送数据] 没有新的 item 需要发送。");
        return;
    }

    // 将新 item 的 outerHTML 拼接成一个字符串
    const htmlContent = Array.from(newItems).map(item => item.outerHTML).join('\n');

    console.log(`[发送数据] 准备发送 ${newItems.length} 个新 item 到服务器...`);

    fetch('http://localhost:8080/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'text/html' // 发送 HTML 片段
        },
        body: htmlContent
    })
    .then(response => {
        if (response.ok) {
            return response.text();
        } else {
            throw new Error(`服务器错误: ${response.status} ${response.statusText}`);
        }
    })
    .then(data => console.log('[发送数据] 服务器响应:', data))
    .catch(error => console.error('[发送数据] 发送数据时出错:', error));
}

function scrollAndCount() {
    if (isProcessing) {
        return;
    }
    isProcessing = true;

    const containers = document.querySelectorAll(scrollContainerSelector);

    if (!containers) {
        stopScrolling();
        isProcessing = false;
        return;
    }
    // inner child is more than 10 element
    const getNotEmptyContainer =  Array.from(containers).find(container => {
        const items = container.querySelectorAll(itemSelector);
        return items.length > 10;
    })
    const itemsBeforeScroll = getNotEmptyContainer.querySelectorAll(itemSelector);
    const lastItem = itemsBeforeScroll.length > 0 ? itemsBeforeScroll[itemsBeforeScroll.length - 1] : null;

    if (lastItem) {
        lastItem.scrollIntoView({ behavior: 'auto', block: 'end' });
    } else {
        container.scrollTop = container.scrollHeight;
    }

    setTimeout(() => {
        const itemsAfterScrollNodeList = document.querySelectorAll(itemSelector);
        const itemsAfterScroll = Array.from(itemsAfterScrollNodeList); // 转换为数组以便使用 slice
        const currentItemCount = itemsAfterScroll.length;

        //  if count changed log else do nothing
        if (currentItemCount !== lastItemCount) {
            console.log(`[统计] 当前找到 ${currentItemCount} 个元素 (${itemSelector})`);
        }

        // --- 新增：检查并发送新 item ---
        if (currentItemCount > processedItemCount) {
            const newItems = itemsAfterScroll.slice(processedItemCount);
            sendNewItemsToServer(newItems);
            processedItemCount = currentItemCount; // 更新已处理的 item 数量
        }
        // --- 发送新 item 结束 ---

        if (currentItemCount === lastItemCount) {
            noNewItemCount++;
        } else {
            noNewItemCount = 0;
        }
        lastItemCount = currentItemCount;

        // 设置一个非常大的阈值，实际上禁用了基于次数的自动停止
        if (noNewItemCount >= 10000000) {
            stopScrolling();
            isProcessing = false;
            return;
        }

        isProcessing = false;

    }, scrollDelay);
}

function startScrolling() {
    if (scrollIntervalId !== null) {
        return;
    }
    isProcessing = false;
    lastItemCount = 0;
    noNewItemCount = 0;
    processedItemCount = 0; // 重置已处理计数
    scrollAndCount(); // 立即执行一次以处理初始项
    scrollIntervalId = setInterval(scrollAndCount, checkInterval);
}

function stopScrolling() {
    if (scrollIntervalId !== null) {
        clearInterval(scrollIntervalId);
        scrollIntervalId = null;
        isProcessing = false;
        console.log("[停止] 滚动已停止。");
    }
}

// 脚本加载提示 (保留一个，或者也去掉)
// console.log("[提示] 脚本已加载。在控制台输入 'startScrolling()' 来启动，输入 'stopScrolling()' 来停止。");