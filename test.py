import ctypes
import time

user32 = ctypes.windll.user32

VK_V = 0x56
VK_CONTROL = 0x11

print("開始測試，請按 Ctrl+V（5 秒）")

start = time.time()
while time.time() - start < 5:
    ctrl = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
    v = user32.GetAsyncKeyState(VK_V) & 0x8000
    if ctrl and v:
        print("偵測到 Ctrl+V")
        time.sleep(0.3)  # 防止狂刷
