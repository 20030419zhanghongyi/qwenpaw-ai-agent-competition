import { useEffect, useRef, useState, type FormEvent } from "react";
import { askGuide } from "@/api/client";
import { useWalk } from "@/state/WalkContext";
import type { LanguageCode } from "@/types";
import { storyT } from "../storyI18n";
import type {
  StoryAgentAnswer,
  StoryAgentContextData,
} from "../types";

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  sources?: StoryAgentAnswer["webSources"];
  sourceLabel?: string;
}

interface StoryAgentDrawerProps {
  open: boolean;
  context?: StoryAgentContextData;
  language?: LanguageCode;
  onClose: () => void;
  ask?: (
    question: string,
    context?: StoryAgentContextData,
  ) => Promise<StoryAgentAnswer>;
}

function contextPrompt(
  question: string,
  context?: StoryAgentContextData,
  language: LanguageCode = "zh-CN",
): string {
  if (!context) return question;
  const facts = context.known_facts?.slice(0, 4).join("；");
  const boundaries = context.fiction_boundaries?.slice(0, 3).join("；");
  const parts = [
    context.chapter_title && `当前章节：${context.chapter_title}`,
    context.chapter_goal && `本章目标：${context.chapter_goal}`,
    facts && `已公开事实：${facts}`,
    boundaries && `虚构边界：${boundaries}`,
    storyT(language, "agentGuardrail"),
    `玩家问题：${question}`,
  ].filter(Boolean);
  return parts.join("\n").slice(0, 1000);
}

async function defaultAsk(
  question: string,
  context?: StoryAgentContextData,
  language = "zh-CN",
): Promise<StoryAgentAnswer> {
  const response = await askGuide({
    poi: context?.poi_name || storyT(language as LanguageCode, "macau"),
    question: contextPrompt(question, context, language as LanguageCode),
    language,
  });
  return {
    text: response.text,
    source: response.source,
    webUsed: response.web_used,
    webSources: response.web_sources,
  };
}

export function StoryAgentDrawer({
  open,
  context,
  language,
  onClose,
  ask,
}: StoryAgentDrawerProps) {
  const { language: appLanguage } = useWalk();
  const effectiveLanguage = language ?? appLanguage;
  const st = (
    key: Parameters<typeof storyT>[1],
    values?: Record<string, string | number>,
  ) => storyT(effectiveLanguage, key, values);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const messageIdRef = useRef(0);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    inputRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, busy, onClose]);

  const submit = async (rawQuestion: string) => {
    const normalized = rawQuestion.trim();
    if (!normalized || busy) return;
    setBusy(true);
    setError(null);
    setQuestion("");
    messageIdRef.current += 1;
    setMessages((current) => [
      ...current,
      { id: messageIdRef.current, role: "user", text: normalized },
    ]);
    try {
      const response = ask
        ? await ask(normalized, context)
        : await defaultAsk(normalized, context, effectiveLanguage);
      messageIdRef.current += 1;
      setMessages((current) => [
        ...current,
        {
          id: messageIdRef.current,
          role: "assistant",
          text: response.text || st("agentIntro"),
          sources: response.webSources,
          sourceLabel:
            response.source ||
            response.webUsed ? "Web" : "AI",
        },
      ]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : st("close"));
      setQuestion(normalized);
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void submit(question);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end justify-center bg-ink/35 sm:items-stretch sm:justify-end"
      role="dialog"
      aria-modal="true"
      aria-labelledby="story-agent-title"
      onClick={onClose}
    >
      <section
        className="flex h-[min(85dvh,720px)] w-full max-w-[480px] flex-col rounded-t-3xl border-t border-line bg-paper shadow-[var(--shadow-lift)] sm:h-full sm:max-w-[430px] sm:rounded-none sm:border-l sm:border-t-0"
        onClick={(event) => event.stopPropagation()}
      >
        <header
          className="flex items-center justify-between border-b border-line px-4 pb-3"
          style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
        >
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ochre">
              {st("agentTitle")}
            </p>
            <h2 id="story-agent-title" className="font-serif text-lg text-ink">
              {st("ask", { persona: context?.persona ?? "A Lin" })}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="grid size-11 place-items-center rounded-full border border-line bg-card text-xl text-ink"
            aria-label={st("close")}
          >
            ×
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 && (
            <div className="rounded-2xl border border-line bg-card p-4">
              <p className="text-base leading-7 text-ink-soft">
                {st("agentIntro")}
              </p>
            </div>
          )}
          {context?.suggested_questions &&
            context.suggested_questions.length > 0 && (
              <div className="mt-4">
                <p className="text-[13px] font-medium text-ink-soft">{st("suggested")}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {context.suggested_questions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      disabled={busy}
                      onClick={() => void submit(suggestion)}
                      className="min-h-11 rounded-full border border-sage/35 bg-sage/10 px-3 text-left text-[13px] text-sage-deep disabled:opacity-45"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
          <div className="mt-4 space-y-3" aria-live="polite">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`max-w-[90%] rounded-2xl px-4 py-3 ${
                  message.role === "user"
                    ? "ml-auto bg-sage-deep text-paper"
                    : "mr-auto border border-line bg-card text-ink"
                }`}
              >
                <p className="text-base leading-7">{message.text}</p>
                {message.role === "assistant" && message.sourceLabel && (
                  <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.12em] opacity-70">
                    {message.sourceLabel}
                  </p>
                )}
                {message.sources && message.sources.length > 0 && (
                  <ul className="mt-2 space-y-1 border-t border-line/50 pt-2 text-[13px]">
                    {message.sources.map((source, index) => (
                      <li key={`${source.url ?? source.title}-${index}`}>
                        {source.url?.startsWith("http") ? (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noreferrer"
                            className="underline underline-offset-2"
                          >
                            {source.title ?? source.source ?? "Source"}
                          </a>
                        ) : (
                          source.title ?? source.source ?? "Source"
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
            {busy && (
              <div className="mr-auto rounded-2xl border border-line bg-card px-4 py-3 text-base text-ink-soft">
                {st("thinking")}
              </div>
            )}
          </div>
          {error && (
            <p role="alert" className="mt-3 rounded-xl border border-clay/30 bg-clay/5 p-3 text-sm text-clay">
              {error}
            </p>
          )}
        </div>

        <form
          onSubmit={onSubmit}
          className="border-t border-line bg-paper px-4 pt-3"
          style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
        >
          <div className="flex gap-2">
            <label className="sr-only" htmlFor="story-agent-question">
              {st("askAlian")}
            </label>
            <input
              ref={inputRef}
              id="story-agent-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              maxLength={500}
              disabled={busy}
              placeholder={st("askPlacePlaceholder")}
              className="min-h-12 min-w-0 flex-1 rounded-full border border-line bg-card px-4 text-base text-ink outline-none placeholder:text-ink-soft/60 focus:border-sage focus:ring-2 focus:ring-sage/30"
            />
            <button
              type="submit"
              disabled={busy || !question.trim()}
              className="min-h-12 shrink-0 rounded-full bg-sage-deep px-5 text-base font-medium text-paper disabled:opacity-45"
            >
              {st("send")}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
