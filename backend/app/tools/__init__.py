"""后端直连的外部能力 / 工具（无状态）。

与 ``app/agents/`` 的区别：agents 走 QwenPaw agent 编排（带技能、会话、降级纪律）；
tools 是后端直接调用的无状态能力或纯函数工具（图片脱敏、地图、TTS…）。

注：拍照识别的「看图」走 QwenPaw ``photo`` agent（``app/agents/photo_agent.py``），
不在这里；这里只放与模型无关的脱敏工具 ``scrub``。
"""
