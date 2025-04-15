import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys
import time
import pyautogui
import json

# 导入核心功能
from auto_download_core import (
    load_saved_coordinates,
    save_coordinates,
    wait_and_locate,
    DOWNLOAD_BTN_IMG,
    NEXT_BTN_IMG,
    RENAME_BTN_IMG,
    PAUSE_BETWEEN_ACTIONS,
    COORDINATES_FILE
)

class AutoDownloadGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("自动下载助手")
        # self.root.geometry("400x300")
        self.root.geometry("400x350")  # 增加高度
        self.root.resizable(False, False)
        
        # 设置应用图标
        try:
            self.root.iconbitmap("download_icon.ico")
        except:
            pass  # 如果没有图标文件，则忽略
        
        # 主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 状态变量
        self.is_running = False
        self.download_thread = None
        self.stop_event = threading.Event()
        
        # 创建界面元素
        self.create_widgets()
        
        # 配置退出处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # 标题
        title_label = ttk.Label(self.main_frame, text="自动下载视频工具", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # 分割线
        separator = ttk.Separator(self.main_frame, orient='horizontal')
        separator.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
        
        # 下载区域框架
        download_frame = ttk.LabelFrame(self.main_frame, text="下载操作", padding=10)
        download_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        
        # 下载操作按钮
        self.start_btn = ttk.Button(download_frame, text="启动下载", command=self.start_download)
        self.start_btn.pack(fill=tk.X, pady=5)
        
        self.stop_btn = ttk.Button(download_frame, text="停止下载", command=self.stop_download, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=5)
        
        self.reset_coords_btn = ttk.Button(download_frame, text="重置坐标", command=self.reset_coordinates)
        self.reset_coords_btn.pack(fill=tk.X, pady=5)
        
        # LLM 上传框架
        llm_frame = ttk.LabelFrame(self.main_frame, text="LLM 上传", padding=10)
        llm_frame.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
        
        # LLM 上传按钮
        self.start_llm_btn = ttk.Button(llm_frame, text="启动上传", command=self.start_llm_upload, state=tk.DISABLED)
        self.start_llm_btn.pack(fill=tk.X, pady=5)
        
        self.stop_llm_btn = ttk.Button(llm_frame, text="停止上传", command=self.stop_llm_upload, state=tk.DISABLED)
        self.stop_llm_btn.pack(fill=tk.X, pady=5)
        
        # 配置按钮
        self.config_llm_btn = ttk.Button(llm_frame, text="配置", command=self.configure_llm, state=tk.DISABLED)
        self.config_llm_btn.pack(fill=tk.X, pady=5)
        
        # 状态显示区域
        status_frame = ttk.Frame(self.main_frame)
        status_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # 设置列和行权重
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

    def start_download(self):
        if self.is_running:
            return
            
        self.is_running = True
        self.stop_event.clear()
        self.status_var.set("下载中...")
        
        # 更新按钮状态
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.reset_coords_btn.config(state=tk.DISABLED)
        
        # 启动下载线程
        self.download_thread = threading.Thread(target=self.download_task)
        self.download_thread.daemon = True
        self.download_thread.start()
        
        # 添加倒计时
        self.countdown(3)
    
    def countdown(self, seconds):
        """倒计时提示用户切换到目标页面"""
        if seconds > 0:
            self.status_var.set(f"请切换到目标页面，{seconds}秒后开始...")
            self.root.after(1000, lambda: self.countdown(seconds - 1))
        
    def download_task(self):
        """下载任务的线程函数"""
        try:
            # 倒计时完成后的额外延迟
            time.sleep(0.5)
            
            # 获取屏幕尺寸
            screen_width, screen_height = pyautogui.size()
            
            while not self.stop_event.is_set():
                # 更新GUI状态 (线程安全)
                self.root.after(0, self.status_var.set, "正在查找下载按钮...")
                
                try:
                    # 1. 定位并点击下载按钮
                    download_btn_pos = wait_and_locate(
                        DOWNLOAD_BTN_IMG, 
                        "download_button",
                        timeout=15,  # 缩短超时时间
                        region=(screen_width//2, 0, screen_width//2, screen_height//2)
                    )
                    
                    if self.stop_event.is_set():
                        break
                        
                    pyautogui.moveTo(download_btn_pos)
                    pyautogui.click()
                    self.root.after(0, self.status_var.set, "已点击下载按钮")
                    time.sleep(PAUSE_BETWEEN_ACTIONS + 2)

                    # 移动到屏幕中央并点击
                    rename_btn_pos = wait_and_locate(
                        RENAME_BTN_IMG, 
                        "rename_button",
                        timeout=15,
                    )
                    pyautogui.moveTo(rename_btn_pos)
                    pyautogui.click()
                    self.root.after(0, self.status_var.set, "移动到屏幕中央并点击")
                    # 按ctrl +v粘贴
                    pyautogui.hotkey('ctrl', 'v')
                    self.root.after(0, self.status_var.set, "已粘贴文件名")
                    time.sleep(PAUSE_BETWEEN_ACTIONS)

                    # 2. IDM快捷键
                    self.root.after(0, self.status_var.set, "按下Alt+S键进行下载")
                    pyautogui.hotkey('alt', 's')
                    time.sleep(PAUSE_BETWEEN_ACTIONS)
                    
                    # 3. 定位并点击下一项按钮
                    self.root.after(0, self.status_var.set, "查找下一项按钮...")
                    next_btn_pos = wait_and_locate(
                        NEXT_BTN_IMG, 
                        "next_button",
                        timeout=15,
                        region=(screen_width//2, 0, screen_width//2, screen_height//2)
                    )
                    
                    if self.stop_event.is_set():
                        break
                        
                    pyautogui.moveTo(next_btn_pos)
                    pyautogui.click()
                    self.root.after(0, self.status_var.set, "已点击下一项按钮")
                    time.sleep(PAUSE_BETWEEN_ACTIONS)
                    
                except Exception as e:
                    self.root.after(0, self.status_var.set, f"出错: {str(e)}")
                    self.root.after(0, messagebox.showerror, "错误", str(e))
                    break
                    
        except Exception as e:
            self.root.after(0, self.status_var.set, f"线程错误: {str(e)}")
        finally:
            # 任务结束后更新GUI
            self.root.after(0, self.reset_gui_after_stop)
    
    def stop_download(self):
        """停止下载任务"""
        if self.is_running and self.download_thread:
            self.stop_event.set()
            self.status_var.set("正在停止...")
    
    def reset_gui_after_stop(self):
        """重置GUI状态"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.reset_coords_btn.config(state=tk.NORMAL)
        self.status_var.set("就绪")
    
    def reset_coordinates(self):
        """重置已保存的坐标"""
        try:
            if os.path.exists(COORDINATES_FILE):
                os.remove(COORDINATES_FILE)
                messagebox.showinfo("成功", "坐标文件已重置")
            else:
                messagebox.showinfo("提示", "没有找到坐标文件")
        except Exception as e:
            messagebox.showerror("错误", f"重置坐标失败: {str(e)}")
    
    def start_llm_upload(self):
        """启动LLM上传功能（待实现）"""
        messagebox.showinfo("提示", "LLM上传功能尚未实现")
    
    def stop_llm_upload(self):
        """停止LLM上传功能（待实现）"""
        pass
    
    def configure_llm(self):
        """配置LLM上传（待实现）"""
        messagebox.showinfo("提示", "LLM配置功能尚未实现")
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if self.is_running:
            if messagebox.askokcancel("退出", "任务正在运行中，确定要退出吗？"):
                self.stop_event.set()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoDownloadGUI(root)
    #  置顶
    root.attributes("-topmost", True)
    root.mainloop()