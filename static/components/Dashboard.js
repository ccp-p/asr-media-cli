// --- 配置 ---
const scrollContainerSelector = 'div.search-super-content-container.search-super-content-links'; // 要滚动的容器的选择器
const itemSelector = 'a.row.row-with-padding.row-clickable.hover-effect.search-super-item'; // 要统计的元素的选择器
const scrollDelay = 100; // 每次滚动后等待的毫秒数
const checkInterval = 100; // setInterval 的间隔时间
// --- 配置结束 ---

let scrollIntervalId = null;
let isProcessing = false;
let lastItemCount = 0;
let noNewItemCount = 0;

function scrollAndCount() {
    if (isProcessing) {
        return;
    }
    isProcessing = true;

    const container = document.querySelector(scrollContainerSelector);

    if (!container) {
        stopScrolling();
        isProcessing = false;
        return;
    }

    const itemsBeforeScroll = container.querySelectorAll(itemSelector);
    const lastItem = itemsBeforeScroll.length > 0 ? itemsBeforeScroll[itemsBeforeScroll.length - 1] : null;

    if (lastItem) {
        lastItem.scrollIntoView({ behavior: 'auto', block: 'end' });
    } else {
        container.scrollTop = container.scrollHeight;
    }

    setTimeout(() => {
        const itemsAfterScroll = document.querySelectorAll(itemSelector);
        const currentItemCount = itemsAfterScroll.length;
        console.log(`[统计] 当前找到 ${currentItemCount} 个元素 (${itemSelector})`);

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
    scrollAndCount();
    scrollIntervalId = setInterval(scrollAndCount, checkInterval);
}

function stopScrolling() {
    if (scrollIntervalId !== null) {
        clearInterval(scrollIntervalId);
        scrollIntervalId = null;
        isProcessing = false;
    }
}

// 脚本加载提示 (保留一个，或者也去掉)
// console.log("[提示] 脚本已加载。在控制台输入 'startScrolling()' 来启动，输入 'stopScrolling()' 来停止。");