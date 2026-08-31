import { useEffect, useState, type FormEvent } from "react";
import { AuthApiError, changePassword, getSecurityQuestion, updateSecurityQuestion } from "@/api/auth";
import { SECURITY_QUESTIONS, securityQuestionLabel } from "@/features/auth/securityQuestions";
import type { LanguageCode } from "@/types";

const copy: Record<LanguageCode, Record<string, string>> = {
  "zh-CN": { title: "密码与找回", change: "修改密码", current: "当前密码", next: "新密码", confirm: "确认新密码", save: "保存新密码", recovery: "安全问题", recoveryLead: "设置后可在忘记密码时验证身份。", choose: "选择安全问题", answer: "安全问题答案", set: "保存安全问题", saved: "已保存", wrong: "当前密码不正确", mismatch: "两次输入的新密码不一致", failed: "暂时无法完成请求", configured: "当前已设置：" },
  "zh-TW": { title: "密碼與找回", change: "修改密碼", current: "目前密碼", next: "新密碼", confirm: "確認新密碼", save: "儲存新密碼", recovery: "安全問題", recoveryLead: "設定後可在忘記密碼時驗證身份。", choose: "選擇安全問題", answer: "安全問題答案", set: "儲存安全問題", saved: "已儲存", wrong: "目前密碼不正確", mismatch: "兩次輸入的新密碼不一致", failed: "暫時無法完成請求", configured: "目前已設定：" },
  en: { title: "Password & recovery", change: "Change password", current: "Current password", next: "New password", confirm: "Confirm new password", save: "Save new password", recovery: "Security question", recoveryLead: "Use this to verify your identity if you forget your password.", choose: "Choose a security question", answer: "Security answer", set: "Save security question", saved: "Saved", wrong: "Current password is incorrect", mismatch: "New passwords do not match", failed: "The request could not be completed", configured: "Currently set: " },
  pt: { title: "Palavra-passe e recuperação", change: "Alterar palavra-passe", current: "Palavra-passe atual", next: "Nova palavra-passe", confirm: "Confirmar nova palavra-passe", save: "Guardar nova palavra-passe", recovery: "Pergunta de segurança", recoveryLead: "Use-a para verificar a identidade se esquecer a palavra-passe.", choose: "Escolha uma pergunta", answer: "Resposta de segurança", set: "Guardar pergunta", saved: "Guardado", wrong: "A palavra-passe atual está incorreta", mismatch: "As novas palavras-passe não coincidem", failed: "Não foi possível concluir o pedido", configured: "Atualmente: " },
};

export function PasswordSettings({ language }: { language: LanguageCode }) {
  const c = copy[language];
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [questionPassword, setQuestionPassword] = useState("");
  const [questionId, setQuestionId] = useState("");
  const [answer, setAnswer] = useState("");
  const [configuredQuestion, setConfiguredQuestion] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getSecurityQuestion()
      .then((result) => setConfiguredQuestion(result.security_question_id))
      .catch(() => undefined);
  }, []);

  const handleError = (requestError: unknown) => {
    setError(requestError instanceof AuthApiError && requestError.status === 401 ? c.wrong : c.failed);
  };

  const submitPassword = async (event: FormEvent) => {
    event.preventDefault();
    setError(null); setMessage(null);
    if (newPassword !== confirmPassword) { setError(c.mismatch); return; }
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword(""); setMessage(c.saved);
    } catch (requestError) { handleError(requestError); }
  };

  const submitQuestion = async (event: FormEvent) => {
    event.preventDefault();
    setError(null); setMessage(null);
    try {
      await updateSecurityQuestion({ current_password: questionPassword, security_question_id: questionId, security_answer: answer });
      setConfiguredQuestion(questionId); setQuestionPassword(""); setAnswer(""); setMessage(c.saved);
    } catch (requestError) { handleError(requestError); }
  };

  const inputClass = "mt-1.5 h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep";
  return (
    <section className="mb-8 rounded-2xl border border-line bg-card px-5 py-5 shadow-[var(--shadow-soft)]">
      <h2 className="font-display text-xl text-ink">{c.title}</h2>
      <div className="mt-5 grid gap-8 md:grid-cols-2">
        <form className="space-y-3" onSubmit={(event) => void submitPassword(event)}>
          <h3 className="font-medium text-ink">{c.change}</h3>
          <label className="block text-sm text-ink">{c.current}<input required type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} className={inputClass} autoComplete="current-password" /></label>
          <label className="block text-sm text-ink">{c.next}<input required minLength={6} type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} className={inputClass} autoComplete="new-password" /></label>
          <label className="block text-sm text-ink">{c.confirm}<input required minLength={6} type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className={inputClass} autoComplete="new-password" /></label>
          <button className="h-11 rounded-full bg-sage-deep px-5 text-sm font-medium text-paper">{c.save}</button>
        </form>
        <form className="space-y-3" onSubmit={(event) => void submitQuestion(event)}>
          <h3 className="font-medium text-ink">{c.recovery}</h3>
          <p className="text-xs text-ink-soft">{configuredQuestion ? c.configured + securityQuestionLabel(configuredQuestion, language) : c.recoveryLead}</p>
          <label className="block text-sm text-ink">{c.current}<input required type="password" value={questionPassword} onChange={(event) => setQuestionPassword(event.target.value)} className={inputClass} autoComplete="current-password" /></label>
          <label className="block text-sm text-ink">{c.recovery}<select required value={questionId} onChange={(event) => setQuestionId(event.target.value)} className={inputClass}><option value="">{c.choose}</option>{SECURITY_QUESTIONS.map((question) => <option key={question.id} value={question.id}>{question.label[language]}</option>)}</select></label>
          <label className="block text-sm text-ink">{c.answer}<input required minLength={2} value={answer} onChange={(event) => setAnswer(event.target.value)} className={inputClass} autoComplete="off" /></label>
          <button className="h-11 rounded-full border border-sage-deep px-5 text-sm font-medium text-sage-deep">{c.set}</button>
        </form>
      </div>
      {error ? <p role="alert" className="mt-4 text-sm text-clay">{error}</p> : null}
      {message ? <p role="status" className="mt-4 text-sm text-sage-deep">{message}</p> : null}
    </section>
  );
}
