#!/usr/bin/env python3
"""
detect_cameras.py

- 打印 macOS 系统识别到的摄像头设备（system_profiler）。
- 用 OpenCV 依次尝试打开索引 0..max_index（默认 8），对每个索引：
    - 打印是否能打开并读取帧 (ret)
    - 若能读取则弹窗显示一小段实时画面并在图像上标注索引/分辨率
- 按 'q' 可以随时退出显示；脚本会在每个设备上停留 show_time 秒（默认 2s）
"""

import cv2
import subprocess
import json
import sys
import time

def list_macos_cameras():
    """
    使用 system_profiler 列出系统识别到的摄像头信息（SPCameraDataType）。
    返回列表（设备名字符串）。如果 system_profiler 不可用或解析失败，则返回空列表。
    """
    try:
        # 以 JSON 输出（macOS 10.13+ 支持）。如果你的 macOS 版本不支持 -json，下面会降级到纯文本解析。
        proc = subprocess.run(["system_profiler", "SPCameraDataType", "-json"], capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            out = proc.stdout.strip()
            if out:
                try:
                    j = json.loads(out)
                    # JSON 的结构在不同 macOS 版本可能不同。遍历找设备名字段。
                    names = []
                    # j usually has top-level key "SPCameraDataType"
                    for k,v in j.items():
                        if isinstance(v, list):
                            for dev in v:
                                # device entries might include _name or "camera" keys
                                if isinstance(dev, dict):
                                    for kk,vv in dev.items():
                                        if isinstance(vv, dict) and "camera" in vv:
                                            # nested pattern
                                            try:
                                                names.append(vv.get("camera", ""))
                                            except:
                                                pass
                                    # fallback check common keys
                                    if "camera" in dev:
                                        names.append(dev.get("camera"))
                                    elif "_name" in dev:
                                        names.append(dev.get("_name"))
                    # remove blanks
                    return [n for n in names if n]
                except json.JSONDecodeError:
                    pass
        # 如果 JSON 路径失败，尝试纯文本解析
        proc2 = subprocess.run(["system_profiler", "SPCameraDataType"], capture_output=True, text=True, timeout=10)
        txt = proc2.stdout
        names = []
        for line in txt.splitlines():
            line = line.strip()
            if line and not line.startswith("Camera:") and ":" in line:
                # 常见行形如 "FaceTime HD Camera (Built-in):"
                if "Camera" in line or "Built-in" in line or "Virtual" in line or "Obs" in line or "OBS" in line:
                    names.append(line)
        return names
    except Exception as e:
        print("无法运行 system_profiler:", e)
        return []

def try_open_index(idx, backend=None):
    """
    尝试以给定索引打开摄像头。backend 可选（cv2 backend flag），返回 (cap, ret, frame_shape)
    """
    try:
        if backend is not None:
            cap = cv2.VideoCapture(idx, backend)
        else:
            cap = cv2.VideoCapture(idx)

        # small delay to let camera warm up
        time.sleep(0.2)
        if not cap.isOpened():
            return None, False, None
        ret, frame = cap.read()
        if not ret or frame is None:
            return cap, False, None
        return cap, True, frame.shape
    except Exception as e:
        print(f"Error opening index {idx}: {e}")
        return None, False, None

def show_camera(cap, idx, show_time=2.0):
    """
    在窗口中显示 cap 捕获的内容，并在图像上标注索引和分辨率。
    显示 show_time 秒或直到按下 'q'。
    """
    start = time.time()
    winname = f"Camera index {idx} (press q to quit)"
    cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            # show blank with text
            canvas = 255 * np.ones((200, 400, 3), dtype='uint8')
            cv2.putText(canvas, f"index {idx} read failed", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            cv2.imshow(winname, canvas)
        else:
            h,w = frame.shape[:2]
            text = f"idx={idx} {w}x{h}"
            cv2.putText(frame, text, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
            cv2.imshow(winname, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return False
        if time.time() - start >= show_time:
            break
    cv2.destroyWindow(winname)
    return True

if __name__ == "__main__":
    import numpy as np

    print("===== macOS system camera list (system_profiler SPCameraDataType) =====")
    cams = list_macos_cameras()
    if cams:
        for i, name in enumerate(cams):
            print(f"sys[{i}]: {name}")
    else:
        print("未能从 system_profiler 获得摄像头列表，可能输出格式不一致或权限限制。")

    max_index = 8
    print("\n===== OpenCV 尝试打开 index 0..{} =====".format(max_index))
    # 首先尝试默认 backend
    results = []
    for idx in range(0, max_index + 1):
        cap, ok, shape = try_open_index(idx)
        print(f"index {idx}: opened={cap is not None and cap.isOpened()}, read_ok={ok}, shape={shape}")
        if ok and cap is not None:
            try:
                cont = show_camera(cap, idx, show_time=2.0)
                # cont=False 表示用户按 q，退出整个脚本
                if not cont:
                    cap.release()
                    print("用户请求退出。")
                    sys.exit(0)
            except Exception as e:
                print("显示时出错:", e)
            cap.release()
        else:
            # 尝试用 AVFoundation backend（macOS 专用）再试一次（某些情况下能改变行为）
            try:
                backend = cv2.CAP_AVFOUNDATION
            except:
                backend = None
            if backend is not None:
                cap2, ok2, shape2 = try_open_index(idx, backend=backend)
                print(f"  retry with AVFOUNDATION: opened={cap2 is not None and cap2.isOpened()}, read_ok={ok2}, shape={shape2}")
                if ok2 and cap2 is not None:
                    try:
                        cont = show_camera(cap2, idx, show_time=2.0)
                        if not cont:
                            cap2.release()
                            print("用户请求退出。")
                            sys.exit(0)
                    except Exception as e:
                        print("显示时出错:", e)
                    cap2.release()
    print("测试完成。请根据上面输出判断哪个索引是真正的内置摄像头。")
    print("提示：如果某个索引能读取帧并且在 system_profiler 输出中你看到了相近的设备名（例如 'FaceTime HD Camera'），那通常该索引就是内置摄像头。")
