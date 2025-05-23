import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from urllib.parse import urlencode

def check_environment():
    """检查Python版本和必要依赖"""
    # 检查Python版本
    if sys.version_info < (3, 6):
        print("\n错误：需要Python 3.6或更高版本")
        print(f"当前Python版本: {sys.version}")
        print("请从 https://www.python.org/downloads/ 下载最新版本")
        input("按任意键退出...")
        sys.exit(1)
    
    # 检查requests包
    try:
        import requests
    except ImportError:
        print("\n错误：缺少必要依赖包 'requests'")
        print("请通过以下命令安装:")
        print("pip3 install requests")
        input("按任意键退出...")
        sys.exit(1)

# 在脚本开始处运行环境检查
check_environment()

# 配置信息
config = {
    "Host": "127.0.0.1",
    "Port": 9784,
    "AccessToken": "114514"  # 接收端验证令牌
}

target_config = {
    "Host": "127.0.0.1",
    "Port": 9785,
    "AccessToken": "114514"  # 发送端验证令牌
}

def print_log(title, data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"\n[{timestamp}] \n=== {title} ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))

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
            "access_token": target_config['AccessToken']  # 携带访问令牌
        })
        
        # 构建转发数据
        modified_data = {
            "message_type": body.get("message_type"),
            "message": body.get("message"),
            "auto_escape": body.get("auto_escape", False)
        }

        # 仅当存在user_id时才添加
        if "user_id" in body:
            modified_data["user_id"] = body["user_id"]
            
        # 仅当存在group_id时才添加
        if "group_id" in body:
            modified_data["group_id"] = body["group_id"]
        
        if modified_data["message_type"] == "group":
            modified_data["group_id"] = body.get("group_id")
            # 对青果骰系的特殊处理，因为正常来说不需要user_id，但是青果却设置了-1
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
            
            # 记录目标服务器响应
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

def run_server():
    server = HTTPServer((config['Host'], config['Port']), RequestHandler)
    print(f"Server running on {config['Host']}:{config['Port']}")
    server.serve_forever()

if __name__ == '__main__':
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")