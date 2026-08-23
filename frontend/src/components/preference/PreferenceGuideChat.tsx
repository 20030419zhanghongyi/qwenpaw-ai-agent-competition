import { useEffect, useRef, useState } from "react";
import { guideIntent, parseIntent } from "@/api/client";
import { t } from "@/i18n";
import { stripChatMarkdown } from "@/lib/chatText";
import { inferPreferenceFromText } from "@/lib/preference";
import type { LanguageCode, Preference } from "@/types";

interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  text: string;
}

interface PreferenceGuideChatProps {
  language: LanguageCode;
  disabled?: boolean;
  formVisible: boolean;
  onApplyPreference: (pref: Preference) => void;
  onReadyChange: (ready: boolean) => void;
  onRevealForm: () => void;
}

function openingMessage(language: LanguageCode): string {
  if (language === "en") {
    return "Welcome to Macau StoryWalk. To help us plan a trip that suits you, may I ask how long you would like to explore Macau this time: half a day, one day, multiple days, or an evening stroll?";
  }
  if (language === "pt") {
    return "Bem-vindo ao Macau StoryWalk. Para prepararmos um roteiro mais adequado, poderia dizer quanto tempo pretende explorar Macau desta vez: meio dia, um dia, vários dias ou um passeio noturno?";
  }
  if (language === "zh-TW") {
    return "您好，歡迎使用澳跡同行。為了替您安排更合適的行程，想先請問您這次預計在澳門遊覽多久呢？可以選擇半日、一日、多日，或夜間漫遊。";
  }
  return "您好，欢迎使用澳迹同行。为了替您安排更合适的行程，想先请问您这次预计在澳门游览多久呢？可以选择半日、一日、多日，或夜间漫游。";
}

export function PreferenceGuideChat({
  language,
  disabled,
  formVisible,
  onApplyPreference,
  onReadyChange,
  onRevealForm,
}: PreferenceGuideChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [userTurn, setUserTurn] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const startedForLang = useRef<string | null>(null);
  const userTextsRef = useRef<string[]>([]);

  useEffect(() => {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  useEffect(() => {
    if (startedForLang.current === language) return;
    startedForLang.current = language;
    setMessages([]);
    setSessionId(undefined);
    setReady(false);
    setUserTurn(0);
    setError(null);
    userTextsRef.current = [];
    onReadyChange(false);
    setMessages([{ id: `a-local-${Date.now()}`, role: "assistant", text: openingMessage(language) }]);
    void startChat(language);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  // 微调区展开后，每轮对话都用全文再回填，保证选项与聊天一致
  useEffect(() => {
    if (!formVisible || userTextsRef.current.length === 0) return;
    onApplyPreference(inferPreferenceFromText(userTextsRef.current.join("\n"), language));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formVisible, userTurn, language]);

  const syncFromTranscript = async () => {
    const transcript = userTextsRef.current.join("\n").trim();
    if (!transcript) return;
    onApplyPreference(inferPreferenceFromText(transcript, language));
    try {
      const parsed = await parseIntent(transcript);
      if (parsed.preference) onApplyPreference(parsed.preference);
      // 本地全文再盖一次，避免 parse 默认 half-day 冲掉已识别时长
      onApplyPreference(inferPreferenceFromText(transcript, language));
    } catch {
      // 解析失败时保留本地推断即可
    }
  };

  const markReady = (value: boolean) => {
    setReady(value);
    if (value) {
      void syncFromTranscript().finally(() => {
        onReadyChange(true);
        onRevealForm();
      });
      return;
    }
    onReadyChange(value);
  };

  const startChat = async (lang: LanguageCode) => {
    try {
      const res = await guideIntent({ action: "start", language: lang });
      if (userTextsRef.current.length === 0) setSessionId(res.session_id);
      if (res.preference) onApplyPreference(res.preference);
      if (res.ready) markReady(true);
    } catch {
      // The local opening remains usable; the first user answer can still use the rule fallback.
    }
  };

  const send = async () => {
    const text = draft.trim();
    if (!text || busy || disabled) return;
    const nextTurn = userTurn + 1;
    setDraft("");
    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: "user", text }]);

    userTextsRef.current = [...userTextsRef.current, text];
    const transcript = userTextsRef.current.join("\n");

    // 用整段对话推断，保证多轮信息累积到下方选项
    onApplyPreference(inferPreferenceFromText(transcript, language));

    setBusy(true);
    setError(null);
    try {
      const res = await guideIntent({
        action: "message",
        session_id: sessionId,
        message: text,
        language,
        user_turn: nextTurn,
        transcript,
      });
      setSessionId(res.session_id);
      setUserTurn(nextTurn);
      setMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: "assistant", text: stripChatMarkdown(res.reply) },
      ]);
      // 后端 preference 先合并；再用全文推断盖住缺省/弱信号（如默认 half-day）
      if (res.preference) onApplyPreference(res.preference);
      onApplyPreference(inferPreferenceFromText(transcript, language));
      // agent 宣布 ready，或聊满 3 轮后自动展开微调区
      if (res.ready || nextTurn >= 3) {
        markReady(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "guide failed";
      setError(
        message.includes("Failed to fetch") ? t(language, "backendDown") : message,
      );
      // 网络失败时，聊过 2 轮也允许展开微调
      if (nextTurn >= 2) markReady(true);
    } finally {
      setBusy(false);
    }
  };

  const canSkip = !formVisible && !disabled;

  const handleSkip = () => {
    setReady(true);
    onReadyChange(true);
    onRevealForm();
  };

  return (
    <section className="mb-10 overflow-hidden rounded-2xl border border-sage-deep/20 bg-sage-deep/[0.04]">
      <div className="border-b border-line/60 px-5 py-4">
        <h2 className="font-display text-xl text-ink">{t(language, "aiGuideTitle")}</h2>
        <p className="mt-1 text-xs leading-relaxed text-ink-soft">
          {t(language, "aiGuideLead")}
        </p>
      </div>

      <div
        ref={scrollerRef}
        className="flex max-h-[420px] min-h-[280px] flex-col gap-3 overflow-y-auto px-5 py-4"
      >
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-sage-deep text-paper"
                  : "border border-line bg-paper text-ink"
              }`}
            >
              {m.role === "assistant" ? stripChatMarkdown(m.text) : m.text}
            </div>
          </div>
        ))}
        {busy ? (
          <div className="flex justify-start">
            <div
              className="flex items-center gap-2 rounded-2xl border border-line bg-paper px-4 py-3 text-ink-soft"
              aria-live="polite"
              aria-label={t(language, "aiGuideParsing")}
            >
              <span className="text-xs">{t(language, "aiGuideParsing")}</span>
              <span
                className="inline-flex items-end gap-[3px] pb-0.5 text-lg leading-none text-sage-deep"
                aria-hidden
              >
                <span className="thinking-dot">.</span>
                <span className="thinking-dot">.</span>
                <span className="thinking-dot">.</span>
              </span>
            </div>
          </div>
        ) : null}
      </div>

      <div className="border-t border-line/60 px-5 py-4">
        <div className="flex gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            disabled={busy || disabled}
            placeholder={t(language, "aiGuidePlaceholder")}
            className="min-w-0 flex-1 rounded-full border border-line bg-paper px-4 py-2.5 text-sm text-ink outline-none ring-sage focus:ring-2"
          />
          {canSkip ? (
            <button
              type="button"
              onClick={handleSkip}
              className="shrink-0 rounded-full border border-line bg-paper px-4 py-2.5 text-sm font-medium text-ink-soft hover:border-sage hover:text-ink"
            >
              {t(language, "aiGuideSkip")}
            </button>
          ) : null}
          <button
            type="button"
            disabled={busy || disabled || !draft.trim()}
            onClick={() => void send()}
            className="shrink-0 rounded-full bg-sage-deep px-5 py-2.5 text-sm font-medium text-paper hover:bg-moss disabled:opacity-60"
          >
            {t(language, "aiGuideSend")}
          </button>
        </div>

        {ready && formVisible ? (
          <p className="mt-2 text-xs text-moss">{t(language, "aiGuideApplied")}</p>
        ) : null}
        {error ? <p className="mt-2 text-xs text-ink-soft">{error}</p> : null}
      </div>
    </section>
  );
}
