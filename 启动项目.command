#!/bin/zsh
# Macau StoryWalk · 一键启动
# 双击本文件 → 自动拉起 QwenPaw(:8088) + 后端 Docker(:8000) + 前端 Vite(:5173) 并打开浏览器
# 已在运行的服务会跳过（不重复启动）。前端日志留在本窗口，Ctrl+C 只停前端。

# ── 还原 PATH（双击 .command 时不读 ~/.zshrc，nvm/docker/conda 都可能不在 PATH）──
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
[ -s "$HOME/.nvm/nvm.sh" ] && \. "$HOME/.nvm/nvm.sh"          # node / npm（nvm）
export PATH="/opt/anaconda3/envs/qwenpaw/bin:$PATH"            # qwenpaw 二进制

PROJECT="/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition"
QWENPAW_BIN="/opt/anaconda3/envs/qwenpaw/bin/qwenpaw"
FE_PORT=5173

cd "$PROJECT" || { echo "❌ 找不到项目目录：$PROJECT"; read "REPLY?按回车关闭..."; exit 1; }

echo "════════════════════════════════════════════"
echo "  Macau StoryWalk · 一键启动"
echo "════════════════════════════════════════════"
echo ""

# ── 1. QwenPaw (:8088) ────────────────────────────────────────
echo "▶ [1/3] 检查 QwenPaw (:8088)..."
if curl -sf -m 2 http://127.0.0.1:8088/api/version >/dev/null 2>&1; then
  echo "   ✓ 已在运行，跳过"
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

# ── 2. 后端 Docker (:8000) ────────────────────────────────────
echo "▶ [2/3] 检查后端 (:8000)..."
if curl -sf -m 2 http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
  echo "   ✓ 已在运行，跳过"
else
  if ! docker info >/dev/null 2>&1; then
    echo "   ⚠ Docker 未运行 —— 请先启动 Docker Desktop，再双击本文件"
    read "REPLY?按回车关闭..."
    exit 1
  fi
  echo "   docker compose up -d（首次或改代码后可能要几十秒）..."
  docker compose up -d
  for i in $(seq 1 90); do
    if curl -sf -m 2 http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
      echo "   ✓ 已就绪（${i}s）"
      break
    fi
    sleep 1
  done
  curl -sf -m 2 http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1 || echo "   ⚠ 后端未就绪，请看 docker compose logs"
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
echo "   API 文档: http://localhost:8000/docs"
echo "   停前端按 Ctrl+C（QwenPaw 与后端会继续运行）"
echo "════════════════════════════════════════════"
echo ""
cd "$PROJECT/frontend"
exec npm run dev
