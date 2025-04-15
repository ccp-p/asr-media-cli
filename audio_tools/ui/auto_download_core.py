import os
import time
import json
import pyautogui

# 获取当前脚本所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 设置图片路径为当前脚本目录下的文件
DOWNLOAD_BTN_IMG = os.path.join(current_dir, 'download_btn.jpg')
NEXT_BTN_IMG = os.path.join(current_dir, 'next_btn.jpg')
RENAME_BTN_IMG = os.path.join(current_dir, 'rename_btn.jpg')
COORDINATES_FILE = os.path.join(current_dir, 'saved_coordinates.json')

PAUSE_BETWEEN_ACTIONS = 2  # 秒

def load_saved_coordinates():
    """从本地文件加载保存的坐标"""
    if os.path.exists(COORDINATES_FILE):
        try:
            with open(COORDINATES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载坐标文件失败: {str(e)}")
    return {}

def save_coordinates(name, position):
    """保存坐标到本地文件"""
    coordinates = load_saved_coordinates()
    try:
        # 处理不同类型的position
        if hasattr(position, 'x') and hasattr(position, 'y'):
            x_coord, y_coord = position.x, position.y
        elif isinstance(position, (list, tuple)) and len(position) >= 2:
            x_coord, y_coord = position[0], position[1]
        else:
            raise TypeError(f"不支持的位置类型: {type(position)}")
            
        coordinates[name] = {"x": int(x_coord), "y": int(y_coord)}
        
        with open(COORDINATES_FILE, 'w') as f:
            json.dump(coordinates, f, indent=2)
        print(f"已保存 {name} 坐标: ({x_coord}, {y_coord})")
    except Exception as e:
        print(f"保存坐标失败: {str(e)}")

def wait_and_locate(image, name, timeout=30, retry_count=3, use_saved=True, region=None):
    """等待并定位图片，返回中心坐标，支持多次重试"""
    # 首先尝试使用保存的坐标
    if use_saved:
        saved_coords = load_saved_coordinates()
        if name in saved_coords:
            coords = saved_coords[name]
            position = (coords["x"], coords["y"])
            print(f"使用保存的坐标 {name}: {position}")
            return position
    
    # 如果没有保存的坐标或不使用保存的坐标，则进行图像识别
    for attempt in range(retry_count):
        try:
            start = time.time()
            while True:
                try:
                    location = pyautogui.locateCenterOnScreen(
                        image, 
                        confidence=0.8,
                        region=region
                    )
                    if location:
                        # 成功识别，保存坐标
                        save_coordinates(name, location)
                        return location
                    if time.time() - start > timeout:
                        break  # 超时后尝试下一次重试
                    time.sleep(0.5)
                except pyautogui.ImageNotFoundException:
                    print(f"未找到图片，继续尝试: {image}")
                    time.sleep(1)
                    continue
        except Exception as e:
            print(f"尝试 {attempt+1}/{retry_count} 失败: {str(e)}")
            
    # 所有重试都失败
    raise TimeoutError(f"多次尝试后未能在屏幕上找到图片: {image}")

def main():
    """独立运行时的主函数"""
    print("3秒后开始自动化操作，请切换到目标页面...")
    print("按 Ctrl+C 可以随时停止脚本")
    
    # 获取屏幕尺寸
    screen_width, screen_height = pyautogui.size()
    print(f"屏幕分辨率: {screen_width}x{screen_height}")
    
    time.sleep(3)
    try:
        while True:
            # 1. 定位并点击下载按钮
            print("查找下载按钮...")
            download_btn_pos = wait_and_locate(
                DOWNLOAD_BTN_IMG, 
                "download_button",
                region=(screen_width//2, 0, screen_width//2, screen_height//2)
            )

            pyautogui.moveTo(download_btn_pos)
            pyautogui.click()
            print("已点击下载按钮")
            time.sleep(PAUSE_BETWEEN_ACTIONS)

            # 2. 出现idm窗口后，按下快捷键
            print("按下Alt+L键进行下载")
            pyautogui.hotkey('alt', 'l')
            time.sleep(PAUSE_BETWEEN_ACTIONS)

            # 3. 定位并点击下一项按钮
            print("查找下一项按钮...")
            next_btn_pos = wait_and_locate(
                NEXT_BTN_IMG, 
                "next_button",
                region=(screen_width//2, 0, screen_width//2, screen_height//2)
            )
            pyautogui.moveTo(next_btn_pos)
            pyautogui.click()
            print("已点击下一项按钮")
            time.sleep(PAUSE_BETWEEN_ACTIONS)
    except KeyboardInterrupt:
        print("用户中断，程序退出")

if __name__ == "__main__":
    main()