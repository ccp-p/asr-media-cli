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
let sentItemIdentifiers = new Set(); // 新增：跟踪已发送 item 的标识符 (outerHTML)
const MAX_ITEMS = 2000; // 新增：最大 item 数量阈值
const ITEMS_TO_REMOVE = 1000; // 新增：达到阈值时要删除的 item 数量

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

    if (!containers || containers.length === 0) { // 检查 containers 是否为空
        console.error("[错误] 找不到滚动容器:", scrollContainerSelector);
        stopScrolling();
        isProcessing = false;
        return;
    }

    // 找到包含足够多子元素的容器
    const getNotEmptyContainer = Array.from(containers).find(container => {
        const items = container.querySelectorAll(itemSelector);
        return items.length > 10; // 或者其他合适的阈值
    });

    if (!getNotEmptyContainer) {
        console.log("[信息] 未找到足够活跃的滚动容器或容器内元素不足。");
        // 考虑是否应该停止或等待
        // stopScrolling(); // 如果确定无法继续，则停止
        isProcessing = false; // 允许下一次尝试
        return;
    }

    // 滚动前获取 item 数量 (用于比较是否新增) - 注意：这里的 lastItemCount 是上个周期的最终数量
    // const itemsBeforeScroll = getNotEmptyContainer.querySelectorAll(itemSelector); // 不再需要

    const container = getNotEmptyContainer.querySelectorAll(itemSelector); // 获取容器内最后一个 item
    const lastItem = container.length > 0 ? container[container.length - 1] : null;

    if (lastItem) {
        lastItem.scrollIntoView({ behavior: 'auto', block: 'end' });
    } else {
        // 如果没有 item，尝试滚动容器本身
        getNotEmptyContainer.scrollTop = getNotEmptyContainer.scrollHeight;
    }

    setTimeout(() => {
        const allItemsNodeList = getNotEmptyContainer.querySelectorAll(itemSelector);
        const allItems = Array.from(allItemsNodeList);
        let currentItemCount = allItems.length;

        //  if count changed log else do nothing
        //  使用 allItems.length 和上个周期的 lastItemCount 比较
        if (currentItemCount !== lastItemCount) {
            console.log(`[统计] 当前找到 ${currentItemCount} 个元素 (${itemSelector})`);
        }

        // --- 新增：使用 Set 检查并发送新 item ---
        const newItems = allItems.filter(item => !sentItemIdentifiers.has(item.outerHTML));
        if (newItems.length > 0) {
            sendNewItemsToServer(newItems);
            newItems.forEach(item => sentItemIdentifiers.add(item.outerHTML)); // 添加已发送 item 的标识符
            console.log(`[发送数据] ${newItems.length} 个新 item 已发送并记录。Set size: ${sentItemIdentifiers.size}`);
        }
        // --- 发送新 item 结束 ---

        // --- 新增：检查并删除旧 item ---
        let itemsWereRemoved = false;
        if (currentItemCount > MAX_ITEMS) {
            console.log(`[维护] Item 数量 (${currentItemCount}) 超过 ${MAX_ITEMS}，准备删除前 ${ITEMS_TO_REMOVE} 个 item。`);
            const itemsToRemove = allItems.slice(0, ITEMS_TO_REMOVE);

            // 从 Set 中移除
            itemsToRemove.forEach(item => sentItemIdentifiers.delete(item.outerHTML));
            // 从 DOM 中移除
            itemsToRemove.forEach(item => item.remove());

            currentItemCount -= ITEMS_TO_REMOVE; // 更新当前计数
            itemsWereRemoved = true;
            console.log(`[维护] 已删除 ${ITEMS_TO_REMOVE} 个旧 item。剩余: ${currentItemCount}。Set size: ${sentItemIdentifiers.size}`);
        }
        // --- 删除旧 item 结束 ---


        // --- 更新停止检查逻辑 ---
        // 比较本周期 *删除后* 的数量 (currentItemCount) 与上周期 *删除后* 的数量 (lastItemCount)
        if (currentItemCount === lastItemCount && !itemsWereRemoved) { // 只有在数量没变且没有执行删除时，才认为没有新内容加载
             noNewItemCount++;
             console.log(`[状态] Item 数量未变 (${currentItemCount}) 且未删除，noNewItemCount = ${noNewItemCount}`);
        } else {
             noNewItemCount = 0; // 只要数量变化或执行了删除，就重置计数器
        }
        lastItemCount = currentItemCount; // 更新 lastItemCount 为本周期 *结束时* 的数量，供下周期比较

        // 设置一个非常大的阈值，实际上禁用了基于次数的自动停止
        if (noNewItemCount >= 10000000) { // 保留原来的大阈值
            console.log(`[停止] 连续 ${noNewItemCount} 次未检测到新 item（且未进行删除），滚动停止。`);
            stopScrolling();
            isProcessing = false;
            return;
        }

        isProcessing = false;

    }, scrollDelay);
}

function startScrolling() {
    if (scrollIntervalId !== null) {
        console.log("[信息] 滚动已在进行中。");
        return;
    }
    console.log("[启动] 开始滚动...");
    isProcessing = false;
    lastItemCount = 0; // 重置上周期数量
    noNewItemCount = 0; // 重置无新项计数
    // processedItemCount = 0; // 不再需要此变量
    sentItemIdentifiers.clear(); // 清空已发送 Set
    scrollAndCount(); // 立即执行一次以处理初始项并开始循环
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