import os
import socket
import threading
import shutil  # 用于压缩和解压文件夹
from tkinter import Tk, Label, Button, filedialog, Text, END, Scrollbar, RIGHT, Y
from tkinter import simpledialog  # 导入 simpledialog 模块
from pathlib import Path  # 用于获取下载目录路径

class FileTransferApp:
    def __init__(self, root):
        self.root = root
        self.server_started = False  # 标志变量
        self.root.title("局域网文件传输工具")
        self.root.geometry("500x400")
        
        self.label = Label(root, text=f"接收端 IP: {socket.gethostbyname(socket.gethostname())}", font=("Arial", 12))
        self.label.pack(pady=5)
        
        self.label = Label(root, text="选择文件或接收文件", font=("Arial", 14))
        self.label.pack(pady=10)
        
        self.send_file_button = Button(root, text="发送文件", command=self.send_file)
        self.send_file_button.pack(pady=5)
        
        self.send_folder_button = Button(root, text="发送文件夹", command=self.send_folder)
        self.send_folder_button.pack(pady=5)
        
        self.receive_button = Button(root, text="接收文件", command=self.start_server)
        self.receive_button.pack(pady=5)
        
        self.log = Text(root, height=15, width=60)
        self.log.pack(pady=10)
        
        scrollbar = Scrollbar(root, command=self.log.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.log['yscrollcommand'] = scrollbar.set

    def log_message(self, message):
        self.log.insert(END, message + "\n")
        self.log.see(END)

    def send_file(self):
        def send_file_thread(file_path, host):
            if not file_path:
                self.log_message("未选择文件")
                return
            if not host:
                self.log_message("未输入目标 IP 地址")
                return
            
            port = 5000
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((host, port))
                    self.log_message(f"连接到 {host}:{port}")
                    
                    file_name = os.path.basename(file_path)
                    s.send(file_name.encode())
                    self.log_message(f"发送文件名: {file_name}")
                    
                    with open(file_path, "rb") as f:
                        while chunk := f.read(1024):
                            s.send(chunk)
                    self.log_message("文件发送完成")
            except Exception as e:
                self.log_message(f"发送失败: {e}")

        # 在主线程中选择文件和输入 IP 地址
        file_path = filedialog.askopenfilename()
        if not file_path:
            self.log_message("未选择文件")
            return

        host = simpledialog.askstring("目标 IP", "请输入接收方的 IP 地址")
        if not host:
            self.log_message("未输入目标 IP 地址")
            return

        # 在后台线程中执行文件发送
        threading.Thread(target=send_file_thread, args=(file_path, host), daemon=True).start()

    def send_folder(self):
        def send_folder_thread(folder_path, host):
            if not folder_path:
                self.log_message("未选择文件夹")
                return
            if not host:
                self.log_message("未输入目标 IP 地址")
                return
            
            port = 5000
            zip_path = folder_path + ".zip"
            
            try:
                # 压缩文件夹
                shutil.make_archive(folder_path, 'zip', folder_path)
                self.log_message(f"文件夹已压缩为: {zip_path}")
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((host, port))
                    self.log_message(f"连接到 {host}:{port}")
                    
                    file_name = os.path.basename(zip_path)
                    s.send(file_name.encode('utf-8'))  # 使用 UTF-8 编码发送文件名
                    self.log_message(f"发送文件夹压缩包: {file_name}")

                    # 等待接收端确认
                    ack = s.recv(1024).decode('utf-8')
                    if ack != "OK":
                        self.log_message("接收端未确认文件名")
                        return

                    with open(zip_path, "rb") as f:
                        while chunk := f.read(1024):
                            s.send(chunk)  # 发送文件内容
                    self.log_message("文件夹发送完成")
                
                # 发送完成后删除压缩包
                os.remove(zip_path)
                self.log_message(f"临时压缩包已删除: {zip_path}")
            except Exception as e:
                self.log_message(f"发送失败: {e}")

        folder_path = filedialog.askdirectory()
        if not folder_path:
            self.log_message("未选择文件夹")
            return

        host = simpledialog.askstring("目标 IP", "请输入接收方的 IP 地址")
        if not host:
            self.log_message("未输入目标 IP 地址")
            return

        threading.Thread(target=send_folder_thread, args=(folder_path, host), daemon=True).start()

    def start_server(self):
        host = "0.0.0.0"
        port = 5000

        def handle_client(conn, addr):
            self.log_message(f"连接来自 {addr}")
            
            # 接收文件名（确保以 UTF-8 解码）
            try:
                raw_data = conn.recv(1024)
                self.log_message(f"接收到的原始数据: {raw_data}")
                file_name = raw_data.decode('utf-8').strip()
                self.log_message(f"接收文件名: {file_name}")

                # 发送确认
                conn.send("OK".encode('utf-8'))
            except UnicodeDecodeError as e:
                self.log_message(f"文件名解码失败: {e}")
                conn.close()
                return
            
            # 获取默认下载目录
            download_dir = str(Path.home() / "Downloads")
            save_path = os.path.join(download_dir, file_name)
            
            # 接收文件内容并保存
            with open(save_path, "wb") as f:
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:  # 文件传输结束
                        break
                    f.write(chunk)
            self.log_message(f"文件接收完成: {save_path}")
            
            # 如果是压缩包，解压到下载目录
            if save_path.endswith(".zip"):
                try:
                    extract_dir = os.path.join(download_dir, os.path.splitext(file_name)[0])
                    shutil.unpack_archive(save_path, extract_dir)
                    self.log_message(f"文件夹已解压到: {extract_dir}")
                    
                    # 删除临时压缩包
                    os.remove(save_path)
                    self.log_message(f"临时压缩包已删除: {save_path}")
                except Exception as e:
                    self.log_message(f"解压失败: {e}")
            
            conn.close()

        def server_thread():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                s.listen(1)
                self.log_message(f"监听中: {host}:{port}")
                
                while True:
                    conn, addr = s.accept()
                    threading.Thread(target=handle_client, args=(conn, addr)).start()

        # 检查服务器是否已启动
        if not self.server_started:
            self.server_started = True
            threading.Thread(target=server_thread, daemon=True).start()
        else:
            self.log_message("服务器已在运行")

        # 获取并显示本机的局域网 IP 地址
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        self.log_message(f"接收端的局域网 IP 地址是: {local_ip}")

if __name__ == "__main__":
    root = Tk()
    app = FileTransferApp(root)
    root.mainloop()