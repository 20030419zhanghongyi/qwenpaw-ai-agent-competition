import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/state/AuthContext";
import type { LanguageCode } from "@/types";

type Mode = "login" | "register";

export function AuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, register, error, clearError, isAuthenticated, isRestoring } = useAuth();
  const initialMode = searchParams.get("mode") === "register" ? "register" : "login";
  const [mode, setMode] = useState<Mode>(initialMode);
  const [userId, setUserId] = useState("");
  const [name, setName] = useState("");
  const [language, setLanguage] = useState<LanguageCode>("zh-CN");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isRestoring && isAuthenticated) {
      navigate("/preferences", { replace: true });
    }
  }, [isAuthenticated, isRestoring, navigate]);

  const changeMode = (nextMode: Mode) => {
    setMode(nextMode);
    clearError();
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedUserId = userId.trim();
    if (!normalizedUserId) return;

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login({ user_id: normalizedUserId });
      } else {
        await register({
          user_id: normalizedUserId,
          name: name.trim() || undefined,
          language,
        });
      }
      navigate("/preferences");
    } catch {
      // The provider exposes the backend error for display.
    } finally {
      setSubmitting(false);
    }
  };

  if (isRestoring) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-paper px-5 py-12">
        <p className="text-sm text-ink-soft">正在恢复登录状态…</p>
      </main>
    );
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-paper px-5 py-12">
      <section className="w-full max-w-md rounded-3xl border border-line bg-card p-6 shadow-[var(--shadow-soft)] sm:p-8">
        <Link to="/" className="text-sm text-ink-soft transition hover:text-ink">
          ← 返回首页
        </Link>
        <h1 className="mt-4 font-display text-3xl text-ink">
          {mode === "login" ? "登录" : "注册"}
        </h1>
        <p className="mt-2 text-sm text-ink-soft">
          使用用户 ID 保存偏好和行程进度。
        </p>

        <div className="mt-6 grid grid-cols-2 rounded-full bg-paper-warm p-1">
          <button
            type="button"
            onClick={() => changeMode("login")}
            className={`rounded-full px-4 py-2 text-sm ${
              mode === "login" ? "bg-sage-deep text-paper" : "text-ink"
            }`}
          >
            登录
          </button>
          <button
            type="button"
            onClick={() => changeMode("register")}
            className={`rounded-full px-4 py-2 text-sm ${
              mode === "register" ? "bg-sage-deep text-paper" : "text-ink"
            }`}
          >
            注册
          </button>
        </div>

        <form className="mt-6 space-y-4" onSubmit={(event) => void submit(event)}>
          <label className="block">
            <span className="mb-1.5 block text-sm text-ink">用户 ID</span>
            <input
              required
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
              autoComplete="username"
            />
          </label>

          {mode === "register" ? (
            <>
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">昵称（可选）</span>
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
                  autoComplete="name"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">语言</span>
                <select
                  value={language}
                  onChange={(event) => setLanguage(event.target.value as LanguageCode)}
                  className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
                >
                  <option value="zh-CN">简体中文</option>
                  <option value="zh-TW">繁體中文</option>
                  <option value="en">English</option>
                  <option value="pt">Português</option>
                </select>
              </label>
            </>
          ) : null}

          {error ? (
            <p role="alert" className="text-sm text-clay">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="h-12 w-full rounded-full bg-sage-deep font-medium text-paper hover:bg-moss disabled:opacity-60"
          >
            {submitting ? "提交中…" : mode === "login" ? "登录" : "注册"}
          </button>
        </form>
      </section>
    </main>
  );
}
