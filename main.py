import tkinter as tk
from tkinter import ttk
import json
import os
import ctypes
import sys

import pyperclip
import psutil
import win32gui
import win32process

# =================================================
# 基本設定
# =================================================
DATA_FILE = "accounts.json"
GENSHIN_EXE = "genshinimpact.exe"
LOGO_FILE = "logo.png"  # 可選
is_visible = False
# =================================================
# 要求系統管理員
# =================================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, __file__, None, 1
    )
    sys.exit(0)

# =================================================
# Win32 鍵盤狀態
# =================================================
user32 = ctypes.windll.user32

VK_CONTROL  = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_V        = 0x56

def key_down(vk):
    return user32.GetAsyncKeyState(vk) & 0x8000

def ctrl_v_down():
    ctrl = (
        key_down(VK_CONTROL) or
        key_down(VK_LCONTROL) or
        key_down(VK_RCONTROL)
    )
    return ctrl and key_down(VK_V)

def exit_app():
    try:
        root.destroy()
    finally:
        sys.exit(0)
# =================================================
# 原神相關
# =================================================
def is_genshin_running():
    for p in psutil.process_iter(["name"]):
        try:
            if p.info["name"] and p.info["name"].lower() == GENSHIN_EXE:
                return True
        except:
            pass
    return False

def get_foreground_hwnd():
    return win32gui.GetForegroundWindow()

def is_genshin_hwnd(hwnd):
    if not hwnd:
        return False
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        return psutil.Process(pid).name().lower() == GENSHIN_EXE
    except:
        return False

def find_genshin_hwnd():
    result = []
    def enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        if is_genshin_hwnd(hwnd):
            result.append(hwnd)
    win32gui.EnumWindows(enum_cb, None)
    return result[0] if result else None

def get_window_pos(hwnd):
    l, t, _, _ = win32gui.GetWindowRect(hwnd)
    return l, t

# =================================================
# 帳號資料
# =================================================
def load_accounts():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("accounts", [])

def save_accounts(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"accounts": data}, f, ensure_ascii=False, indent=2)

accounts = load_accounts()
current_index = None

# =================================================
# 登入流程狀態
# =================================================
FLOW_IDLE = 0
FLOW_WAIT_RELEASE = 1

flow_state = FLOW_IDLE
active_password = None
last_ctrl_v = False

# =================================================
# Ctrl+V 偵測（放開才切密碼 + 清空剪貼簿）
# =================================================
def poll_keys():
    global last_ctrl_v, flow_state, active_password

    now = ctrl_v_down()
    fg_hwnd = get_foreground_hwnd()

    if now and not last_ctrl_v and is_genshin_hwnd(fg_hwnd):
        if flow_state == FLOW_IDLE and active_password:
            flow_state = FLOW_WAIT_RELEASE
            status.set("帳號已貼上，放開 Ctrl+V 後切換密碼")

    if not now and last_ctrl_v:
        if flow_state == FLOW_WAIT_RELEASE:
            pyperclip.copy(active_password)
            status.set("已切換為密碼，請再 Ctrl+V")
            flow_state = FLOW_IDLE
            active_password = None
        else:
            pyperclip.copy("")
            status.set("登入完成，剪貼簿已清空")

    last_ctrl_v = now
    root.after(15, poll_keys)

# =================================================
# UI
# =================================================
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.95)

app_hwnds = set()

def register_hwnd(widget):
    try:
        app_hwnds.add(widget.winfo_id())
    except:
        pass

register_hwnd(root)

# ---------- Logo Frame ----------
logo_frame = ttk.Frame(root, padding=4)
logo_frame.pack()

try:
    if os.path.exists(LOGO_FILE):
        logo_img = tk.PhotoImage(file=LOGO_FILE)
        logo_label = ttk.Label(logo_frame, image=logo_img)
    else:
        raise FileNotFoundError
except:
    logo_label = ttk.Label(logo_frame, text="GI", font=("Segoe UI", 18, "bold"))

logo_label.pack()
logo_label.bind("<Button-1>", lambda e: show_main())

# ---------- Main Frame ----------
main_frame = ttk.Frame(root, padding=8)

combo = ttk.Combobox(main_frame, state="readonly")
combo.pack(fill="x")

status = tk.StringVar(value="選擇帳號以開始")

def refresh_combo():
    combo["values"] = [a["name"] for a in accounts]

refresh_combo()

def on_select(event=None):
    global current_index, active_password, flow_state
    name = combo.get()
    for i, a in enumerate(accounts):
        if a["name"] == name:
            current_index = i
            pyperclip.copy(a["username"])
            active_password = a["password"]
            flow_state = FLOW_IDLE
            status.set("已複製帳號，請在原神 Ctrl+V")
            break

combo.bind("<<ComboboxSelected>>", on_select)

ttk.Label(main_frame, textvariable=status).pack()

def editor(edit):
    global current_index
    if edit and current_index is None:
        return

    win = tk.Toplevel(root)
    win.geometry("260x180")
    register_hwnd(win)

    def save():
        name = e_name.get().strip()
        user = e_user.get().strip()
        pwd = e_pwd.get().strip()
        if not name or not user or not pwd:
            return
        if edit:
            accounts[current_index] = {"name": name, "username": user, "password": pwd}
        else:
            accounts.append({"name": name, "username": user, "password": pwd})
        save_accounts(accounts)
        refresh_combo()
        win.destroy()

    ttk.Label(win, text="名稱").pack()
    e_name = ttk.Entry(win)
    e_name.pack(fill="x", padx=10)

    ttk.Label(win, text="帳號").pack()
    e_user = ttk.Entry(win)
    e_user.pack(fill="x", padx=10)

    ttk.Label(win, text="密碼").pack()
    e_pwd = ttk.Entry(win)
    e_pwd.pack(fill="x", padx=10)

    if edit:
        a = accounts[current_index]
        e_name.insert(0, a["name"])
        e_user.insert(0, a["username"])
        e_pwd.insert(0, a["password"])

    ttk.Button(win, text="儲存", command=save).pack(pady=8)

ttk.Button(main_frame, text="新增帳號", command=lambda: editor(False)).pack(fill="x", pady=2)
ttk.Button(main_frame, text="編輯帳號", command=lambda: editor(True)).pack(fill="x", pady=2)
ttk.Button(main_frame, text="縮小", command=lambda: show_logo()).pack(fill="x", pady=6)
ttk.Button(
    main_frame,
    text="關閉程式",
    command=exit_app
).pack(fill="x", pady=2)
def show_logo():
    main_frame.pack_forget()
    logo_frame.pack()
    root.geometry("60x60")

def show_main():
    logo_frame.pack_forget()
    main_frame.pack(fill="both", expand=True)
    root.geometry("260x260")

show_logo()

# =================================================
# 跟隨 + 顯示 + 原神關閉即結束
# =================================================
def follow_visibility_and_lifecycle():
    # 原神已關閉 → 程式結束
    if not is_genshin_running():
        root.destroy()
        sys.exit(0)

    hwnd = find_genshin_hwnd()
    fg = get_foreground_hwnd()

    # 跟隨原神位置（這個可以每次做，沒副作用）
    if hwnd:
        x, y = get_window_pos(hwnd)
        root.geometry(f"+{x+10}+{y+30}")

    should_show = is_genshin_hwnd(fg) or is_app_foreground()

    if should_show:
        show_overlay()
    else:
        hide_overlay()

    root.after(500, follow_visibility_and_lifecycle)

def is_app_foreground():
    fg = win32gui.GetForegroundWindow()
    if not fg:
        return False
    _, pid = win32process.GetWindowThreadProcessId(fg)
    return pid == os.getpid()

def show_overlay():
    global is_visible
    if not is_visible:
        root.deiconify()
        is_visible = True

def hide_overlay():
    global is_visible
    if is_visible:
        root.withdraw()
        is_visible = False

def set_topmost(enable: bool):
    root.attributes("-topmost", enable)
# =================================================
# 啟動
# =================================================
follow_visibility_and_lifecycle()
poll_keys()
root.mainloop()
