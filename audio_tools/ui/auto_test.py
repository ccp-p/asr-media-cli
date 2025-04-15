import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import time
from PIL import ImageGrab, Image, ImageTk

class ButtonLocator:
    def __init__(self, root):
        self.root = root
        self.root.title("按钮位置识别与记录工具")
        self.root.geometry("800x1200")
        
        # 坐标保存文件
        self.coordinates_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'button_coordinates.json')
        
        # 保存的坐标字典
        self.coordinates = self.load_coordinates()
        
        # 当前选择的按钮名称
        self.current_button = tk.StringVar(value="rename_btn")
        
        # 截图和预览相关变量
        self.screenshot = None
        self.screenshot_region = None
        self.preview_img = None
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 按钮名称选择框
        button_frame = ttk.LabelFrame(main_frame, text="按钮设置", padding=10)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(button_frame, text="按钮名称:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # 预定义的按钮类型
        predefined_buttons = ["download_btn", "next_button", "rename_btn", "close_button", "custom_button"]
        
        button_combo = ttk.Combobox(button_frame, textvariable=self.current_button, values=predefined_buttons)
        button_combo.grid(row=0, column=1, padx=5, pady=5, sticky="we")
        
        # 自定义名称输入
        ttk.Label(button_frame, text="自定义名称:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.custom_name = ttk.Entry(button_frame)
        self.custom_name.grid(row=1, column=1, padx=5, pady=5, sticky="we")
        
        ttk.Button(button_frame, text="使用自定义名称", command=self.use_custom_name).grid(row=1, column=2, padx=5, pady=5)
        
        # 操作按钮框架
        actions_frame = ttk.LabelFrame(main_frame, text="操作", padding=10)
        actions_frame.pack(fill=tk.X, pady=5)
        
        # 按钮截取方式
        ttk.Label(actions_frame, text="截取方式:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.capture_mode = tk.StringVar(value="screen_region")
        ttk.Radiobutton(actions_frame, text="选择屏幕区域", variable=self.capture_mode, value="screen_region").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(actions_frame, text="鼠标点击位置", variable=self.capture_mode, value="mouse_click").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # 操作按钮
        ttk.Button(actions_frame, text="1. 截取按钮图像", command=self.capture_button).grid(row=1, column=0, padx=5, pady=5, columnspan=2, sticky="we")
        ttk.Button(actions_frame, text="2. 测试识别", command=self.test_recognition).grid(row=1, column=2, padx=5, pady=5, sticky="we")
        
        # 预览框架
        preview_frame = ttk.LabelFrame(main_frame, text="按钮预览", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="lightgray")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 坐标框架
        coords_frame = ttk.LabelFrame(main_frame, text="保存的坐标", padding=10)
        coords_frame.pack(fill=tk.X, pady=5)
        
        # 创建表格来显示保存的坐标
        columns = ("name", "x", "y")
        self.coords_tree = ttk.Treeview(coords_frame, columns=columns, show="headings")
        
        # 设置列标题
        self.coords_tree.heading("name", text="按钮名称")
        self.coords_tree.heading("x", text="X坐标")
        self.coords_tree.heading("y", text="Y坐标")
        
        # 设置列宽度
        self.coords_tree.column("name", width=150)
        self.coords_tree.column("x", width=100)
        self.coords_tree.column("y", width=100)
        
        self.coords_tree.pack(fill=tk.BOTH, expand=True)
        
        # 更新坐标显示
        self.update_coords_tree()
        
        # 底部按钮
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(bottom_frame, text="保存所有坐标", command=self.save_coordinates).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="删除所选坐标", command=self.delete_selected_coordinate).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="退出", command=self.root.destroy).pack(side=tk.RIGHT, padx=5)
    
    def use_custom_name(self):
        """使用用户输入的自定义名称"""
        custom = self.custom_name.get().strip()
        if custom:
            self.current_button.set(custom)
            messagebox.showinfo("成功", f"已设置按钮名称为: {custom}")
        else:
            messagebox.showwarning("警告", "请先输入自定义名称")
    
    def capture_button(self):
        """截取按钮图像"""
        self.root.iconify()  # 最小化窗口
        time.sleep(1)  # 等待窗口隐藏
        
        try:
            if self.capture_mode.get() == "screen_region":
                # 截取区域
                messagebox.showinfo("提示", "请使用鼠标框选按钮区域")
                self.screenshot_region = pyautogui.screenshot()
                region = pyautogui.dragRectangle()
                if region[2] < 10 or region[3] < 10:  # 区域太小
                    messagebox.showwarning("警告", "选择的区域太小，请重试")
                    return
                
                # 截取指定区域
                self.screenshot = ImageGrab.grab(bbox=region)
                
                # 保存按钮图像
                button_name = self.current_button.get()
                img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{button_name}.jpg')
                self.screenshot.save(img_path)
                
                # 显示预览
                self.show_preview(self.screenshot)
                
                messagebox.showinfo("成功", f"已保存按钮图像: {img_path}")
                
            else:  # 鼠标点击
                messagebox.showinfo("提示", "请将鼠标移动到按钮位置并点击")
                time.sleep(1)
                
                # 等待用户点击
                position = None
                while position is None:
                    if pyautogui.mouseDown():
                        position = pyautogui.position()
                        break
                    time.sleep(0.1)
                
                if position:
                    # 保存坐标
                    button_name = self.current_button.get()
                    self.coordinates[button_name] = {"x": position.x, "y": position.y}
                    
                    # 更新坐标树
                    self.update_coords_tree()
                    
                    # 截取鼠标周围区域用于预览
                    region = (position.x - 50, position.y - 50, 100, 100)
                    self.screenshot = ImageGrab.grab(bbox=region)
                    
                    # 显示预览
                    self.show_preview(self.screenshot)
                    
                    messagebox.showinfo("成功", f"已记录按钮位置: ({position.x}, {position.y})")
        finally:
            self.root.deiconify()  # 恢复窗口
    
    def test_recognition(self):
        """测试按钮识别"""
        button_name = self.current_button.get()
        img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{button_name}.jpg')
        
        if not os.path.exists(img_path):
            messagebox.showwarning("警告", f"按钮图像不存在: {img_path}")
            return
        
        self.root.iconify()  # 最小化窗口
        time.sleep(1)  # 等待窗口隐藏
        
        try:
            messagebox.showinfo("提示", "将开始测试识别按钮，请切换到目标窗口")
            time.sleep(2)
            
            try:
                # 尝试找到按钮图像
                location = pyautogui.locateCenterOnScreen(img_path, confidence=0.7)
                
                if location:
                    # 保存找到的位置
                    self.coordinates[button_name] = {"x": int(location.x), "y": int(location.y)}
   
                    self.update_coords_tree()
                    
                    # 高亮位置
                    pyautogui.moveTo(location.x, location.y, duration=0.5)
                    
                    messagebox.showinfo("成功", f"找到按钮位置: ({location.x}, {location.y})")
                else:
                    messagebox.showwarning("警告", "未能在屏幕上找到按钮图像")
            except Exception as e:
                messagebox.showerror("错误", f"识别过程出错: {str(e)}")
        finally:
            self.root.deiconify()  # 恢复窗口
    
    def load_coordinates(self):
        """从文件加载保存的坐标"""
        if os.path.exists(self.coordinates_file):
            try:
                with open(self.coordinates_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载坐标文件失败: {str(e)}")
        return {}
    
    def save_coordinates(self):
        """保存坐标到文件"""
        try:
            with open(self.coordinates_file, 'w') as f:
                json.dump(self.coordinates, f, indent=2)
            messagebox.showinfo("成功", f"坐标已保存到: {self.coordinates_file}")
        except Exception as e:
            messagebox.showerror("错误", f"保存坐标失败: {str(e)}")
    
    def update_coords_tree(self):
        """更新坐标表格显示"""
        # 清除现有项
        for item in self.coords_tree.get_children():
            self.coords_tree.delete(item)
        
        # 添加所有保存的坐标
        for name, coords in self.coordinates.items():
            self.coords_tree.insert("", tk.END, values=(name, coords["x"], coords["y"]))
    
    def delete_selected_coordinate(self):
        """删除选中的坐标"""
        selection = self.coords_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择要删除的坐标")
            return
        
        item = selection[0]
        name = self.coords_tree.item(item, "values")[0]
        
        if name in self.coordinates:
            del self.coordinates[name]
            self.update_coords_tree()
            messagebox.showinfo("成功", f"已删除坐标: {name}")
    
    def show_preview(self, image):
        """在预览区域显示图像"""
        if image:
            # 调整图像大小以适应预览区域
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width <= 1:  # 如果Canvas还没有正确调整大小
                canvas_width = 500
                canvas_height = 300
            
            # 保持纵横比缩放图像
            img_width, img_height = image.size
            ratio = min(canvas_width / img_width, canvas_height / img_height)
            new_size = (int(img_width * ratio), int(img_height * ratio))
            
            resized_img = image.resize(new_size, Image.LANCZOS)
            self.preview_img = ImageTk.PhotoImage(resized_img)
            
            # 清除之前的内容并显示新图像
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                canvas_width // 2, 
                canvas_height // 2, 
                image=self.preview_img,
                anchor=tk.CENTER
            )

if __name__ == "__main__":
    root = tk.Tk()
    app = ButtonLocator(root)
    root.mainloop()