"""图片脱敏（隐私，对齐开发计划 Phase 4 + 伦理最小包「图片去 EXIF」）。

``scrub(image_bytes) -> bytes`` 做两件事：
1. **EXIF/XMP/ICC 全剥离**：用像素重建一张新图（``Image.fromarray``），元数据天然不保留。
2. **人脸高斯模糊**：OpenCV haarcascade 正脸检测 → 局部高斯模糊贴回。离线、无 API。

不做的事（在 docstring + 前端提示里写明）：
- **车牌模糊**：无可靠离线检测器；靠前端提示用户「避免拍到车牌/途人/住宅」。
- 输出统一为 JPEG（照片场景，最小且 VL 模型友好）；透明 PNG 会被合成到 RGB。

失败哲学：人脸检测任何异常都跳过（不阻断上传），但 EXIF 剥离（重建图）恒成立。
"""

from __future__ import annotations

import io
import logging
import os

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("macau_storywalk.scrub")

# OpenCV 自带正脸级联（随 opencv-python / -headless 一起装）
_CASCADE_NAME = "haarcascade_frontalface_default.xml"


def _blur_faces(arr: np.ndarray) -> np.ndarray:
    """对 RGB uint8 数组里检测到的正脸区域做高斯模糊，原位返回。检测失败则原样返回。"""
    try:
        cascade_path = os.path.join(cv2.data.haarcascades, _CASCADE_NAME)
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            logger.info("haarcascade 未就绪，跳过人脸模糊（EXIF 仍已剥离）")
            return arr
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        for x, y, w, h in faces:
            x, y = max(0, int(x)), max(0, int(y))
            w, h = int(w), int(h)
            if w <= 0 or h <= 0:
                continue
            face = arr[y : y + h, x : x + w]
            arr[y : y + h, x : x + w] = cv2.GaussianBlur(face, (0, 0), sigmaX=30)
        logger.info("人脸模糊：%d 张", len(faces))
    except Exception as exc:  # noqa: BLE001 — 人脸模糊失败不应阻断上传
        logger.warning("人脸模糊跳过：%s", exc)
    return arr


def scrub(image_bytes: bytes) -> bytes:
    """剥离全部元数据 + 模糊正脸，返回 JPEG bytes。

    无论人脸检测成不成功，返回的图都已是「无 EXIF 的重建图」。
    """
    img = Image.open(io.BytesIO(image_bytes))
    rgb = img.convert("RGB")  # 合成透明通道，统一为 3 通道
    arr = np.array(rgb)  # 可写副本
    arr = _blur_faces(arr)
    clean = Image.fromarray(arr)  # 全新图，无任何元数据
    out = io.BytesIO()
    clean.save(out, format="JPEG", quality=92)
    return out.getvalue()
