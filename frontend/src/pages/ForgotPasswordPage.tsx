import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AuthApiError, getRecoveryQuestion, resetPassword } from "@/api/auth";
import { securityQuestionLabel } from "@/features/auth/securityQuestions";
import { useWalk } from "@/state/WalkContext";
import type { LanguageCode } from "@/types";

const copy: Record<LanguageCode, Record<string, string>> = {
  "zh-CN": {
    title: "找回密码", lead: "先验证邮箱和安全问题，再设置新密码。", email: "注册邮箱",
    next: "下一步", answer: "安全问题答案", password: "新密码", confirm: "确认新密码",
    reset: "重置密码", success: "密码已重置，现在可以登录。", login: "返回登录",
    home: "← 返回首页", unavailable: "该邮箱没有配置安全问题，无法通过此方式找回。", wrong: "安全问题答案不正确。",
    mismatch: "两次输入的密码不一致。", failed: "暂时无法完成密码重置。",
  },
  "zh-TW": {
    title: "找回密碼", lead: "先驗證電郵和安全問題，再設定新密碼。", email: "註冊電郵",
    next: "下一步", answer: "安全問題答案", password: "新密碼", confirm: "確認新密碼",
    reset: "重設密碼", success: "密碼已重設，現在可以登入。", login: "返回登入",
    home: "← 返回首頁", unavailable: "該電郵未設定安全問題，無法透過此方式找回。", wrong: "安全問題答案不正確。",
    mismatch: "兩次輸入的密碼不一致。", failed: "暫時無法完成密碼重設。",
  },
  en: {
    title: "Recover password", lead: "Verify your email and security answer, then set a new password.", email: "Account email",
    next: "Continue", answer: "Security answer", password: "New password", confirm: "Confirm new password",
    reset: "Reset password", success: "Password reset. You can now log in.", login: "Back to login",
    home: "← Back to home", unavailable: "Password recovery is not configured for this email.", wrong: "The security answer is incorrect.",
    mismatch: "Passwords do not match.", failed: "Password reset could not be completed.",
  },
  pt: {
    title: "Recuperar palavra-passe", lead: "Verifique o e-mail e a resposta de segurança e defina uma nova palavra-passe.", email: "E-mail da conta",
    next: "Continuar", answer: "Resposta de segurança", password: "Nova palavra-passe", confirm: "Confirmar nova palavra-passe",
    reset: "Repor palavra-passe", success: "Palavra-passe reposta. Já pode iniciar sessão.", login: "Voltar ao início de sessão",
    home: "← Voltar ao início", unavailable: "A recuperação não está configurada para este e-mail.", wrong: "A resposta de segurança está incorreta.",
    mismatch: "As palavras-passe não coincidem.", failed: "Não foi possível repor a palavra-passe.",
  },
};

export function ForgotPasswordPage() {
  const { language } = useWalk();
  const c = copy[language];
  const [email, setEmail] = useState("");
  const [questionId, setQuestionId] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const findQuestion = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await getRecoveryQuestion(email.trim());
      setQuestionId(response.security_question_id);
    } catch (requestError) {
      setError(requestError instanceof AuthApiError && requestError.status === 404 ? c.unavailable : c.failed);
    } finally {
      setLoading(false);
    }
  };

  const submitReset = async (event: FormEvent) => {
    event.preventDefault();
    if (!questionId) return;
    if (password !== confirmPassword) {
      setError(c.mismatch);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await resetPassword({
        email: email.trim(), security_question_id: questionId,
        security_answer: answer.trim(), new_password: password,
      });
      setSuccess(true);
    } catch (requestError) {
      setError(requestError instanceof AuthApiError && requestError.status === 401 ? c.wrong : c.failed);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-dvh items-center justify-center bg-paper px-5 py-12">
      <section className="w-full max-w-md rounded-3xl border border-line bg-card p-6 shadow-[var(--shadow-soft)] sm:p-8">
        <Link to="/" className="text-sm text-ink-soft transition hover:text-ink">
          {c.home}
        </Link>
        <h1 className="mt-4 font-display text-3xl text-ink">{c.title}</h1>
        <p className="mt-2 text-sm text-ink-soft">{c.lead}</p>
        {success ? (
          <div className="mt-6">
            <p role="status" className="rounded-xl bg-sage-deep/10 p-4 text-sm text-sage-deep">{c.success}</p>
            <Link to="/auth" className="mt-4 inline-flex text-sm text-sage-deep underline">{c.login}</Link>
          </div>
        ) : !questionId ? (
          <form className="mt-6 space-y-4" onSubmit={(event) => void findQuestion(event)}>
            <label className="block text-sm text-ink">{c.email}
              <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1.5 h-11 w-full rounded-xl border border-line bg-paper px-4 outline-none focus:border-sage-deep" />
            </label>
            {error ? <p role="alert" className="text-sm text-clay">{error}</p> : null}
            <button disabled={loading} className="h-12 w-full rounded-full bg-sage-deep text-paper disabled:opacity-60">{c.next}</button>
            <Link to="/auth" className="block text-center text-sm text-sage-deep underline">{c.login}</Link>
          </form>
        ) : (
          <form className="mt-6 space-y-4" onSubmit={(event) => void submitReset(event)}>
            <p className="rounded-xl bg-paper-warm p-3 text-sm text-ink">{securityQuestionLabel(questionId, language)}</p>
            <label className="block text-sm text-ink">{c.answer}<input required value={answer} onChange={(event) => setAnswer(event.target.value)} className="mt-1.5 h-11 w-full rounded-xl border border-line bg-paper px-4 outline-none focus:border-sage-deep" autoComplete="off" /></label>
            <label className="block text-sm text-ink">{c.password}<input required minLength={6} type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1.5 h-11 w-full rounded-xl border border-line bg-paper px-4 outline-none focus:border-sage-deep" autoComplete="new-password" /></label>
            <label className="block text-sm text-ink">{c.confirm}<input required minLength={6} type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="mt-1.5 h-11 w-full rounded-xl border border-line bg-paper px-4 outline-none focus:border-sage-deep" autoComplete="new-password" /></label>
            {error ? <p role="alert" className="text-sm text-clay">{error}</p> : null}
            <button disabled={loading} className="h-12 w-full rounded-full bg-sage-deep text-paper disabled:opacity-60">{c.reset}</button>
          </form>
        )}
      </section>
    </main>
  );
}
