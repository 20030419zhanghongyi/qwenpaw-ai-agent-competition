#!/bin/zsh
# Macau StoryWalk · 一键启动
# 双击本文件 → 自动拉起 QwenPaw(:8088) + 后端 Docker(:8001) + 前端 Vite(:5173) 并打开浏览器
# 已在运行的服务会跳过（不重复启动）。前端日志留在本窗口，Ctrl+C 只停前端。

# ── 还原 PATH（双击 .command 时不读 ~/.zshrc，nvm/docker/conda 都可能不在 PATH）──
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
[ -s "$HOME/.nvm/nvm.sh" ] && \. "$HOME/.nvm/nvm.sh"          # node / npm（nvm）
export PATH="/opt/anaconda3/envs/qwenpaw/bin:$PATH"            # qwenpaw 二进制

PROJECT="$(cd "$(dirname "$0")" && pwd)"
QWENPAW_BIN="${QWENPAW_BIN:-qwenpaw}"
FE_PORT=5173
BE_PORT="${BACKEND_PUBLISHED_PORT:-8001}"
if command -v npm >/dev/null 2>&1; then
  FRONTEND_RUNNER=(npm run dev)
elif command -v pnpm >/dev/null 2>&1; then
  FRONTEND_RUNNER=(pnpm run dev)
else
  FRONTEND_RUNNER=()
fi

cd "$PROJECT" || { echo "❌ 找不到项目目录：$PROJECT"; read "REPLY?按回车关闭..."; exit 1; }

echo "════════════════════════════════════════════"
echo "  Macau StoryWalk · 一键启动"
echo "════════════════════════════════════════════"
echo ""

# ── 1. QwenPaw (:8088) ────────────────────────────────────────
echo "▶ [1/3] 检查 QwenPaw (:8088)..."
if curl -sf -m 2 http://127.0.0.1:8088/api/version >/dev/null 2>&1; then
  echo "   ✓ 已在运行，跳过"
elif ! command -v "$QWENPAW_BIN" >/dev/null 2>&1; then
  echo "   ⚠ 未找到 QwenPaw 命令：$QWENPAW_BIN"
  echo "   如已安装在特殊路径，可这样启动：QWENPAW_BIN=/path/to/qwenpaw ./启动项目.command"
else
  echo "   启动中（后台）..."
  nohup "$QWENPAW_BIN" app > /tmp/qwenpaw-launch.log 2>&1 &
  for i in $(seq 1 40); do
    curl -sf -m 2 http://127.0.0.1:8088/api/version >/dev/null 2>&1 && { echo "   ✓ 已就绪（${i}s）"; break; }
    sleep 1
  done
  curl -sf -m 2 http://127.0.0.1:8088/api/version >/dev/null 2>&1 || {
    echo "   ⚠ QwenPaw 未就绪，详见 /tmp/qwenpaw-launch.log"
  }
fi
echo ""

# ── 2. 后端 Docker (:8001) ────────────────────────────────────
echo "▶ [2/3] 检查后端 (:${BE_PORT})..."
if curl -sf -m 2 "http://127.0.0.1:${BE_PORT}/api/v1/health" >/dev/null 2>&1; then
  echo "   ✓ 已在运行，跳过"
else
  if ! docker info >/dev/null 2>&1; then
    echo "   ⚠ 无法连接 Docker —— 请先启动 Docker Desktop，并确认当前终端可执行 docker info"
    read "REPLY?按回车关闭..."
    exit 1
  fi
  echo "   docker compose up -d（首次或改代码后可能要几十秒）..."
  docker compose up -d
  for i in $(seq 1 90); do
    if curl -sf -m 2 "http://127.0.0.1:${BE_PORT}/api/v1/health" >/dev/null 2>&1; then
      echo "   ✓ 已就绪（${i}s）"
      break
    fi
    sleep 1
  done
  curl -sf -m 2 "http://127.0.0.1:${BE_PORT}/api/v1/health" >/dev/null 2>&1 || echo "   ⚠ 后端未就绪，请看 docker compose logs"
fi
echo ""

# ── 3. 前端 Vite (:5173) ──────────────────────────────────────
echo "▶ [3/3] 检查前端 (:${FE_PORT})..."
FE_UP=0
# 注意：Vite 默认监听 IPv6 [::1]，不监听 127.0.0.1，故用 localhost（解析到 ::1）
if curl -sf -m 2 http://localhost:${FE_PORT} >/dev/null 2>&1; then
  echo "   ✓ 已在运行，跳过"
  FE_UP=1
fi
echo ""

# ── 打开浏览器 ────────────────────────────────────────────────
echo "🌐 打开浏览器 http://localhost:${FE_PORT}"
open "http://localhost:${FE_PORT}"
echo ""

if [ "$FE_UP" = "1" ]; then
  echo "════════════════════════════════════════════"
  echo "✅ 全部就绪 —— QwenPaw / 后端 / 前端均在运行。"
  echo "   （关掉本窗口不影响后台服务）"
  echo "════════════════════════════════════════════"
  read "REPLY?按回车关闭本窗口..."
  exit 0
fi

echo "════════════════════════════════════════════"
echo "✅ 启动前端 Vite（日志如下，支持热更新）"
echo "   浏览器:  http://localhost:${FE_PORT}"
echo "   API 文档: http://localhost:${BE_PORT}/docs"
echo "   停前端按 Ctrl+C（QwenPaw 与后端会继续运行）"
echo "════════════════════════════════════════════"
echo ""
cd "$PROJECT/frontend"
if [ "${#FRONTEND_RUNNER[@]}" -eq 0 ]; then
  echo "   ⚠ 未找到 npm 或 pnpm。请先安装 Node.js 18+，或通过 nvm 启用 Node。"
  read "REPLY?按回车关闭..."
  exit 1
fi
exec "${FRONTEND_RUNNER[@]}"
