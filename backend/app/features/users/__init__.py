"""用户落库 + 极简登录功能切片（F1）。

注册/登录落 PostgreSQL，偏好整体以 JSON 持久化；
JWT 鉴权（core/security）仅做 token，DB 侧解析在本模块。
"""
