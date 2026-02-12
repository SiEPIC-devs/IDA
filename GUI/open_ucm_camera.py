
import cv2
import time
import tkinter as tk
from tkinter import messagebox
import numpy as np

def _show_error(message):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Camera Error", message)
    root.destroy()

def _open_first_available_camera(indices):
    for idx in indices:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap, idx
    return None, None

print("Opening UCMOS camera...")

# Try common indices first
candidate_indices = [1, 2, 3, 0, 4]
cap, opened_index = _open_first_available_camera(candidate_indices)

if cap is None:
    _show_error("No available camera was found. Please check the camera connection.")
    raise SystemExit(1)

print(f"Camera opened successfully (index {opened_index}).")
print(f"Resolution: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
print("\nPress 'q' to quit, or close the window directly.")

window_name = "UCMOS Camera - Press 'q' to quit"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, 800, 600)

# Warm up a few frames
for _ in range(10):
    cap.read()
    time.sleep(0.02)

while True:
    ret, frame = cap.read()
    
    if ret:
        # Horizontal flip (mirror left-right)
        frame = cv2.flip(frame, 1)
        try:
            _, _, win_w, win_h = cv2.getWindowImageRect(window_name)
        except Exception:
            win_w, win_h = 0, 0

        if win_w <= 0 or win_h <= 0:
            win_h, win_w = frame.shape[:2]

        fh, fw = frame.shape[:2]
        scale = min(win_w / fw, win_h / fh)
        new_w = max(1, int(fw * scale))
        new_h = max(1, int(fh * scale))

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((win_h, win_w, 3), dtype=frame.dtype)
        x = (win_w - new_w) // 2
        y = (win_h - new_h) // 2
        canvas[y:y + new_h, x:x + new_w] = resized

        cv2.imshow(window_name, canvas)
    else:
        print("Failed to read frame.")
        break
    
    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
    # Detect if the window is closed
    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()
print("Camera closed.")
