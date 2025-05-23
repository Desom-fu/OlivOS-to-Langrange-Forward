import json
import requests
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from urllib.parse import urlencode
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading

# 获取当前脚本所在目录
if getattr(sys, 'frozen', False):
    # 打包后的可执行文件路径
    application_path = os.path.dirname(sys.executable)
else:
    # 脚本文件路径
    application_path = os.path.dirname(os.path.abspath(__file__))

# 配置文件路径（与可执行文件同一目录）
CONFIG_FILE = os.path.join(application_path, "config.txt")

# 全局配置变量
config = {}
target_config = {}

# 转发服务默认值
defaults = {
    "local_host": "127.0.0.1",
    "local_port": "9784",
    "local_token": "114514",
    "target_host": "127.0.0.1",
    "target_port": "9785",
    "target_token": "114514"
}

class GUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OlivOS to Langrange HTTP 转发服务配置")
        
        # 转发服务状态
        self.server_running = False
        self.server_thread = None
        self.server = None
        
        # 加载上次的配置
        self.load_config()
        
        # 创建主界面
        self.create_main_frame()
        
        # 重定向print到日志框
        self.redirect_print_to_log()
        
        # 窗口关闭时保存配置
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_main_frame(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置框架（左右并排）
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 接收配置（左）
        self.create_local_config(config_frame)
        
        # 转发配置（右）
        self.create_target_config(config_frame)
        
        # 日志输出
        self.create_log_output(main_frame)
        
        # 控制按钮
        self.create_control_buttons(main_frame)
    
    def create_local_config(self, parent):
        frame = ttk.LabelFrame(parent, text="接收配置", padding=10)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ttk.Label(frame, text="Host:").grid(row=0, column=0, sticky="e", pady=2)
        self.local_host = ttk.Entry(frame)
        self.local_host.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        self.local_host.insert(0, defaults["local_host"])  # 使用字典中的默认值

        ttk.Label(frame, text="Port:").grid(row=1, column=0, sticky="e", pady=2)
        self.local_port = ttk.Entry(frame)
        self.local_port.grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        self.local_port.insert(0, defaults["local_port"])  # 使用字典中的默认值

        ttk.Label(frame, text="AccessToken:").grid(row=2, column=0, sticky="e", pady=2)
        self.local_token = ttk.Entry(frame)
        self.local_token.grid(row=2, column=1, sticky="ew", pady=2, padx=5)
        self.local_token.insert(0, defaults["local_token"])  # 使用字典中的默认值

        # 设置列权重使输入框可以拉伸
        frame.columnconfigure(1, weight=1)

    def create_target_config(self, parent):
        frame = ttk.LabelFrame(parent, text="转发配置", padding=10)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        ttk.Label(frame, text="Host:").grid(row=0, column=0, sticky="e", pady=2)
        self.target_host = ttk.Entry(frame)
        self.target_host.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        self.target_host.insert(0, defaults["target_host"])  # 使用字典中的默认值

        ttk.Label(frame, text="Port:").grid(row=1, column=0, sticky="e", pady=2)
        self.target_port = ttk.Entry(frame)
        self.target_port.grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        self.target_port.insert(0, defaults["target_port"])  # 使用字典中的默认值

        ttk.Label(frame, text="AccessToken:").grid(row=2, column=0, sticky="e", pady=2)
        self.target_token = ttk.Entry(frame)
        self.target_token.grid(row=2, column=1, sticky="ew", pady=2, padx=5)
        self.target_token.insert(0, defaults["target_token"])  # 使用字典中的默认值

        # 设置列权重使输入框可以拉伸
        frame.columnconfigure(1, weight=1)
    
    def create_log_output(self, parent):
        frame = ttk.LabelFrame(parent, text="转发服务日志", padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(frame, width=80, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def create_control_buttons(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_button = ttk.Button(frame, text="开启转发服务", command=self.toggle_server)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="保存配置", command=self.save_config).pack(side=tk.RIGHT, padx=5)
    
    def redirect_print_to_log(self):
        import sys
        class PrintRedirector:
            def __init__(self, text_widget):
                self.text_widget = text_widget
            
            def write(self, text):
                self.text_widget.insert(tk.END, text)
                self.text_widget.see(tk.END)
            
            def flush(self):
                pass
        
        sys.stdout = PrintRedirector(self.log_text)
        sys.stderr = PrintRedirector(self.log_text)
    
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 更新默认值
                    defaults.update(data)
                    print(f"从 {CONFIG_FILE} 加载配置成功")
            else:
                print(f"配置文件 {CONFIG_FILE} 不存在，使用默认配置")
            
            # 填充到界面
            if hasattr(self, 'local_host'):
                self.local_host.delete(0, tk.END)
                self.local_host.insert(0, defaults["local_host"])
                
                self.local_port.delete(0, tk.END)
                self.local_port.insert(0, defaults["local_port"])
                
                self.local_token.delete(0, tk.END)
                self.local_token.insert(0, defaults["local_token"])
                
                self.target_host.delete(0, tk.END)
                self.target_host.insert(0, defaults["target_host"])
                
                self.target_port.delete(0, tk.END)
                self.target_port.insert(0, defaults["target_port"])
                
                self.target_token.delete(0, tk.END)
                self.target_token.insert(0, defaults["target_token"])
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            print("将使用默认配置")
    
    def save_config(self):
        config = {
            "local_host": self.local_host.get(),
            "local_port": self.local_port.get(),
            "local_token": self.local_token.get(),
            "target_host": self.target_host.get(),
            "target_port": self.target_port.get(),
            "target_token": self.target_token.get()
        }
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"配置已保存到 {CONFIG_FILE}")
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def toggle_server(self):
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()
    
    def start_server(self):
        global config, target_config

        try:
            # 获取所有字段值
            local_host = self.local_host.get().strip()
            local_port = self.local_port.get().strip()
            local_token = self.local_token.get().strip()
            target_host = self.target_host.get().strip()
            target_port = self.target_port.get().strip()
            target_token = self.target_token.get().strip()

            # 验证必填字段
            if not all([local_host, local_port, local_token, target_host, target_port, target_token]):
                print("错误: 所有配置字段都必须填写!")
                return

            config = {
                "Host": local_host,
                "Port": int(local_port),
                "AccessToken": local_token
            }

            target_config = {
                "Host": target_host,
                "Port": int(target_port),
                "AccessToken": target_token
            }

            # 保存配置
            self.save_config()

            # 创建转发服务并启动接口线程
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()

            self.server_running = True
            self.start_button.config(text="停止转发服务")
            print(f"转发服务已启动，监听 {config['Host']}:{config['Port']}")

        except ValueError as e:
            print(f"配置错误: {e}")
    
    def stop_server(self):
        if self.server:
            # 关闭转发服务
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        
        self.server_running = False
        self.start_button.config(text="启动转发服务")
        print("转发服务已停止")
    
    def run_server(self):
        class RequestHandler(BaseHTTPRequestHandler):
            def _send_response(self, code, data):
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))

            def _parse_body(self):
                content_length = int(self.headers.get('Content-Length', 0))
                raw_body = self.rfile.read(content_length).decode('utf-8')
                try:
                    return json.loads(raw_body)
                except:
                    return raw_body

            def do_POST(self):
                # 获取并记录原始数据
                body = self._parse_body()
                print_log("收到原始数据", body)

                # 认证验证
                if self.headers.get('Authorization') != f"Bearer {config['AccessToken']}":
                    self._send_response(401, {"status": "unauthorized"})
                    return

                # 处理数据
                if not isinstance(body, dict):
                    self._send_response(400, {"status": "invalid JSON"})
                    return

                # 从self.path中移除token部分
                clean_path = self.path.split('?')[0]
                
                # 构造转发路径
                forward_path = clean_path + "?" + urlencode({
                    "access_token": target_config['AccessToken']
                })
                
                # 构建转发数据
                modified_data = {
                    "message_type": body.get("message_type"),
                    "message": body.get("message"),
                    "auto_escape": body.get("auto_escape", False)
                }

                if "user_id" in body:
                    modified_data["user_id"] = body["user_id"]
                    
                if "group_id" in body:
                    modified_data["group_id"] = body["group_id"]
                
                if modified_data["message_type"] == "group":
                    modified_data["group_id"] = body.get("group_id")
                    modified_data.pop("user_id", None)

                # 记录转发信息
                print_log("转发构造数据", {
                    "path": forward_path,
                    "data": modified_data
                })

                # 发送转发请求
                try:
                    response = requests.post(
                        url=f"http://{target_config['Host']}:{target_config['Port']}{forward_path}",
                        json=modified_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=5
                    )
                    
                    print_log("转发响应", {
                        "status": response.status_code,
                        "data": response.json()
                    })
                    
                    self._send_response(200, {"status": "success"})
                except Exception as e:
                    print_log("转发异常", {
                        "error": str(e),
                        "target": f"{target_config['Host']}:{target_config['Port']}{forward_path}"
                    })
                    self._send_response(502, {"status": "forward failed"})
        
        def print_log(title, data):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"\n[{timestamp}] \n=== {title} ===")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        
        try:
            self.server = HTTPServer((config['Host'], config['Port']), RequestHandler)
            print(f"Server running on {config['Host']}:{config['Port']}")
            self.server.serve_forever()
        except Exception as e:
            print(f"转发服务错误: {e}")
            self.stop_server()
    
    def on_close(self):
        self.save_config()
        if self.server_running:
            self.stop_server()
        self.root.destroy()

def main():
    root = tk.Tk()
    # 设置窗口最小大小
    root.minsize(600, 400)
    app = GUIApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()