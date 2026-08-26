import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/state/AuthContext";
import { useWalk } from "@/state/WalkContext";
import { AuthApiError } from "@/api/auth";
import { t } from "@/i18n";
import type { LanguageCode } from "@/types";

type Mode = "login" | "register";
type TouchedField = "email" | "phone" | "password" | "confirmPassword" | "name";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const MIN_PASSWORD_LENGTH = 6;

/** Common countries and calling codes (ISO 3166-1 alpha-2). */
const COUNTRIES: {
  code: string;
  dialCode: string;
  label: Record<LanguageCode, string>;
}[] = [
  { code: "CN", dialCode: "+86", label: { "zh-CN": "中国大陆", "zh-TW": "中國大陸", en: "China", pt: "China" } },
  { code: "HK", dialCode: "+852", label: { "zh-CN": "中国香港", "zh-TW": "中國香港", en: "Hong Kong", pt: "Hong Kong" } },
  { code: "MO", dialCode: "+853", label: { "zh-CN": "中国澳门", "zh-TW": "中國澳門", en: "Macau", pt: "Macau" } },
  { code: "TW", dialCode: "+886", label: { "zh-CN": "中国台湾", "zh-TW": "中國台灣", en: "Taiwan", pt: "Taiwan" } },
  { code: "JP", dialCode: "+81", label: { "zh-CN": "日本", "zh-TW": "日本", en: "Japan", pt: "Japão" } },
  { code: "KR", dialCode: "+82", label: { "zh-CN": "韩国", "zh-TW": "韓國", en: "South Korea", pt: "Coreia do Sul" } },
  { code: "SG", dialCode: "+65", label: { "zh-CN": "新加坡", "zh-TW": "新加坡", en: "Singapore", pt: "Singapura" } },
  { code: "MY", dialCode: "+60", label: { "zh-CN": "马来西亚", "zh-TW": "馬來西亞", en: "Malaysia", pt: "Malásia" } },
  { code: "TH", dialCode: "+66", label: { "zh-CN": "泰国", "zh-TW": "泰國", en: "Thailand", pt: "Tailândia" } },
  { code: "PH", dialCode: "+63", label: { "zh-CN": "菲律宾", "zh-TW": "菲律賓", en: "Philippines", pt: "Filipinas" } },
  { code: "US", dialCode: "+1", label: { "zh-CN": "美国", "zh-TW": "美國", en: "United States", pt: "Estados Unidos" } },
  { code: "CA", dialCode: "+1", label: { "zh-CN": "加拿大", "zh-TW": "加拿大", en: "Canada", pt: "Canadá" } },
  { code: "GB", dialCode: "+44", label: { "zh-CN": "英国", "zh-TW": "英國", en: "United Kingdom", pt: "Reino Unido" } },
  { code: "PT", dialCode: "+351", label: { "zh-CN": "葡萄牙", "zh-TW": "葡萄牙", en: "Portugal", pt: "Portugal" } },
  { code: "FR", dialCode: "+33", label: { "zh-CN": "法国", "zh-TW": "法國", en: "France", pt: "França" } },
  { code: "DE", dialCode: "+49", label: { "zh-CN": "德国", "zh-TW": "德國", en: "Germany", pt: "Alemanha" } },
  { code: "AU", dialCode: "+61", label: { "zh-CN": "澳大利亚", "zh-TW": "澳洲", en: "Australia", pt: "Austrália" } },
  { code: "BR", dialCode: "+55", label: { "zh-CN": "巴西", "zh-TW": "巴西", en: "Brazil", pt: "Brasil" } },
];

const DEFAULT_PHONE_REGION: Record<LanguageCode, string> = {
  "zh-CN": "CN",
  "zh-TW": "MO",
  en: "MO",
  pt: "PT",
};

const LANGUAGE_LABELS: Record<LanguageCode, string> = {
  "zh-CN": "简体中文",
  "zh-TW": "繁體中文",
  en: "English",
  pt: "Português",
};

export function AuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, register, error, clearError, isAuthenticated, isRestoring } = useAuth();
  const { language } = useWalk();

  const initialMode = searchParams.get("mode") === "register" ? "register" : "login";
  const requestedReturnTo = searchParams.get("returnTo");
  const explicitReturnTo =
    requestedReturnTo?.startsWith("/") && !requestedReturnTo.startsWith("//")
      ? requestedReturnTo
      : null;
  const [mode, setMode] = useState<Mode>(initialMode);
  const successDestination = explicitReturnTo ?? (mode === "login" ? "/walk" : "/preferences");
  const [email, setEmail] = useState("");
  const [phoneRegion, setPhoneRegion] = useState(() => DEFAULT_PHONE_REGION[language]);
  const [phoneRegionOpen, setPhoneRegionOpen] = useState(false);
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [credentialError, setCredentialError] = useState<"account" | "password" | null>(null);
  const [touchedFields, setTouchedFields] = useState<Partial<Record<TouchedField, boolean>>>({});
  const phoneRegionMenuRef = useRef<HTMLDivElement>(null);
  const selectedPhoneRegion =
    COUNTRIES.find((item) => item.code === phoneRegion) ?? COUNTRIES[0];
  const emailInvalid = Boolean(email.trim()) && !EMAIL_PATTERN.test(email.trim());
  const passwordMissing = !password;
  const passwordTooShort = Boolean(password) && password.length < MIN_PASSWORD_LENGTH;
  const confirmPasswordInvalid = mode === "register" && confirmPassword !== password;
  const nicknameMissing = mode === "register" && !name.trim();
  const contactMissing = !email.trim() && !phone.trim();

  const touchField = (field: TouchedField) => {
    setTouchedFields((current) => ({ ...current, [field]: true }));
  };

  useEffect(() => {
    if (!isRestoring && isAuthenticated) {
      navigate(successDestination, { replace: true });
    }
  }, [isAuthenticated, isRestoring, navigate, successDestination]);

  useEffect(() => {
    if (!phoneRegionOpen) return;

    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!phoneRegionMenuRef.current?.contains(event.target as Node)) {
        setPhoneRegionOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPhoneRegionOpen(false);
    };

    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [phoneRegionOpen]);

  const changeMode = (nextMode: Mode) => {
    setMode(nextMode);
    clearError();
    setFormError(null);
    setCredentialError(null);
    setTouchedFields({});
  };

  const goBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }
    navigate("/", { replace: true });
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouchedFields({
      email: true,
      phone: true,
      password: true,
      confirmPassword: mode === "register",
      name: mode === "register",
    });
    const normalizedEmail = email.trim() || null;
    const phoneDigits = phone.replace(/\D/g, "");
    const dialCode = COUNTRIES.find((item) => item.code === phoneRegion)?.dialCode ?? "+853";
    const normalizedPhone = phoneDigits ? `${dialCode}${phoneDigits}` : null;
    setFormError(null);
    setCredentialError(null);
    if (
      (!normalizedEmail && !normalizedPhone) ||
      emailInvalid ||
      passwordMissing ||
      passwordTooShort ||
      confirmPasswordInvalid ||
      nicknameMissing
    ) {
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login({ email: normalizedEmail, phone: normalizedPhone, password: password });
      } else {
        const normalizedName = name.trim();
        if (!normalizedName) return;
        if (password !== confirmPassword) {
          setFormError(t(language, "authPasswordMismatch"));
          return;
        }
        await register({
          email: normalizedEmail,
          phone: normalizedPhone,
          password,
          name: normalizedName,
          language,
          country: country || null,
        });
      }
      navigate(successDestination);
    } catch (requestError) {
      clearError();
      if (requestError instanceof AuthApiError) {
        if (mode === "login" && requestError.status === 404) {
          setCredentialError("account");
        } else if (mode === "login" && requestError.status === 401) {
          setCredentialError("password");
        } else if (mode === "register" && requestError.status === 409) {
          setFormError(t(language, "authAccountExists"));
        } else {
          setFormError(t(language, "authRequestFailed"));
        }
      } else {
        setFormError(t(language, "authRequestFailed"));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const updatePhone = (value: string) => {
    const compact = value.replace(/[\s()-]/g, "");
    if (compact.startsWith("+")) {
      const region = [...COUNTRIES]
        .sort((left, right) => right.dialCode.length - left.dialCode.length)
        .find((item) => compact.startsWith(item.dialCode));
      if (region) {
        setPhoneRegion(region.code);
        setPhone(compact.slice(region.dialCode.length).replace(/\D/g, ""));
        setFormError(null);
        setCredentialError(null);
        return;
      }
    }
    setPhone(value.replace(/\D/g, ""));
    setFormError(null);
    setCredentialError(null);
  };

  if (isRestoring) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-paper px-5 py-12">
        <p className="text-sm text-ink-soft">{t(language, "restoringSession")}</p>
      </main>
    );
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-paper px-5 py-12">
      <section className="w-full max-w-md rounded-3xl border border-line bg-card p-6 shadow-[var(--shadow-soft)] sm:p-8">
        <button
          type="button"
          onClick={goBack}
          className="text-sm text-ink-soft transition hover:text-ink"
        >
          {t(language, "back")}
        </button>
        <h1 className="mt-4 font-display text-3xl text-ink">
          {mode === "login" ? t(language, "authLoginTab") : t(language, "authRegisterTab")}
        </h1>
        <p className="mt-2 text-sm text-ink-soft">
          {t(language, "authPrompt")}
        </p>

        {/* Mode toggle */}
        <div className="mt-6 grid grid-cols-2 rounded-full bg-paper-warm p-1">
          <button
            type="button"
            onClick={() => changeMode("login")}
            className={`rounded-full px-4 py-2 text-sm ${
              mode === "login" ? "bg-sage-deep text-paper" : "text-ink"
            }`}
          >
            {t(language, "authLoginTab")}
          </button>
          <button
            type="button"
            onClick={() => changeMode("register")}
            className={`rounded-full px-4 py-2 text-sm ${
              mode === "register" ? "bg-sage-deep text-paper" : "text-ink"
            }`}
          >
            {t(language, "authRegisterTab")}
          </button>
        </div>

        <form
          className="mt-6 space-y-4"
          noValidate
          onSubmit={(event) => void submit(event)}
        >
          {/* Email */}
          <label className="block">
            <span className="mb-1.5 block text-sm text-ink">{t(language, "authEmail")}</span>
            <input
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setFormError(null);
                setCredentialError(null);
              }}
              onBlur={() => touchField("email")}
              placeholder={t(language, "authEmailPlaceholder")}
              aria-invalid={Boolean(touchedFields.email && emailInvalid) || (credentialError === "account" && Boolean(email.trim()))}
              aria-describedby={
                touchedFields.email && emailInvalid
                  ? "email-error"
                  : credentialError === "account" && email.trim()
                    ? "account-email-error"
                    : undefined
              }
              className={`h-11 w-full rounded-xl border bg-paper px-4 text-ink outline-none focus:border-sage-deep ${
                (touchedFields.email && emailInvalid) ||
                (credentialError === "account" && email.trim())
                  ? "border-clay"
                  : "border-line"
              }`}
              autoComplete="email"
            />
            {touchedFields.email && emailInvalid ? (
              <p id="email-error" role="alert" className="mt-1.5 text-xs text-clay">
                {t(language, "authEmailInvalid")}
              </p>
            ) : credentialError === "account" && email.trim() ? (
              <p id="account-email-error" role="alert" className="mt-1.5 text-xs text-clay">
                {t(language, "authNoAccountFound")}
              </p>
            ) : null}
          </label>

          {/* Phone */}
          <fieldset>
            <legend className="mb-1.5 text-sm text-ink">{t(language, "authPhone")}</legend>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-[12rem_minmax(0,1fr)]">
              <div ref={phoneRegionMenuRef} className="relative min-w-0">
                <span className="mb-1 block text-xs text-ink-soft">
                  {t(language, "authPhoneRegion")}
                </span>
                <button
                  type="button"
                  aria-label={t(language, "authPhoneRegion")}
                  aria-haspopup="listbox"
                  aria-expanded={phoneRegionOpen}
                  onClick={() => setPhoneRegionOpen((open) => !open)}
                  className="flex h-11 w-full items-center gap-2 rounded-xl border border-line bg-paper px-3 text-ink outline-none focus:border-sage-deep"
                >
                  <span className="shrink-0 tabular-nums">{selectedPhoneRegion.dialCode}</span>
                  <span className="min-w-0 flex-1 truncate text-right">
                    {selectedPhoneRegion.label[language] ?? selectedPhoneRegion.label.en}
                  </span>
                  <span
                    aria-hidden="true"
                    className={`shrink-0 text-xs text-ink-soft transition-transform ${
                      phoneRegionOpen ? "rotate-180" : ""
                    }`}
                  >
                    ▾
                  </span>
                </button>
                {phoneRegionOpen ? (
                  <div
                    role="listbox"
                    aria-label={t(language, "authPhoneRegion")}
                    className="absolute left-0 z-30 mt-1 max-h-64 min-w-full overflow-y-auto rounded-xl border border-line bg-card p-1 shadow-[var(--shadow-soft)] sm:w-72"
                  >
                    {COUNTRIES.map((item) => {
                      const selected = item.code === phoneRegion;
                      return (
                        <button
                          key={item.code}
                          type="button"
                          role="option"
                          aria-selected={selected}
                          onClick={() => {
                            setPhoneRegion(item.code);
                            setPhoneRegionOpen(false);
                            setFormError(null);
                            setCredentialError(null);
                          }}
                          className={`grid w-full grid-cols-[4rem_minmax(0,1fr)_1rem] items-center gap-2 rounded-lg px-3 py-2 text-sm transition hover:bg-paper-warm focus:bg-paper-warm focus:outline-none ${
                            selected ? "text-sage-deep" : "text-ink"
                          }`}
                        >
                          <span className="text-left tabular-nums">{item.dialCode}</span>
                          <span className="truncate text-right">
                            {item.label[language] ?? item.label.en}
                          </span>
                          <span aria-hidden="true" className="text-center">
                            {selected ? "✓" : ""}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
              <label className="min-w-0">
                <span className="mb-1 block text-xs text-ink-soft">
                  {t(language, "authPhoneNumber")}
                </span>
                <input
                  type="tel"
                  inputMode="numeric"
                  value={phone}
                  onChange={(event) => updatePhone(event.target.value)}
                  onBlur={() => touchField("phone")}
                  placeholder={t(language, "authPhonePlaceholder")}
                  aria-invalid={credentialError === "account" && !email.trim()}
                  aria-describedby={
                    credentialError === "account" && !email.trim()
                      ? "account-phone-error"
                      : undefined
                  }
                  className={`h-11 w-full rounded-xl border bg-paper px-4 text-ink outline-none focus:border-sage-deep ${
                    credentialError === "account" && !email.trim()
                      ? "border-clay"
                      : "border-line"
                  }`}
                  autoComplete="tel-national"
                  maxLength={18}
                />
              </label>
            </div>
            {touchedFields.email && touchedFields.phone && contactMissing ? (
              <p role="alert" className="mt-1.5 text-xs text-clay">
                {t(language, "authEmailOrPhone")}
              </p>
            ) : credentialError === "account" && !email.trim() ? (
              <p id="account-phone-error" role="alert" className="mt-1.5 text-xs text-clay">
                {t(language, "authNoAccountFound")}
              </p>
            ) : null}
          </fieldset>

          {/* Password — both modes */}
          <label className="block">
            <span className="mb-1.5 block text-sm text-ink">{t(language, "authPassword")}</span>
            <input
              required
              type="password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setFormError(null);
                setCredentialError(null);
              }}
              onBlur={() => touchField("password")}
              placeholder={mode === "register" ? t(language, "authPasswordPlaceholder") : t(language, "authPasswordPlaceholderLogin")}
              aria-invalid={
                Boolean(touchedFields.password && (passwordMissing || passwordTooShort)) ||
                credentialError === "password"
              }
              aria-describedby={
                touchedFields.password && (passwordMissing || passwordTooShort)
                  ? "password-error"
                  : credentialError === "password"
                    ? "password-incorrect-error"
                  : undefined
              }
              className={`h-11 w-full rounded-xl border bg-paper px-4 text-ink outline-none focus:border-sage-deep ${
                (touchedFields.password && (passwordMissing || passwordTooShort)) ||
                credentialError === "password"
                  ? "border-clay"
                  : "border-line"
              }`}
              autoComplete={mode === "register" ? "new-password" : "current-password"}
            />
            {touchedFields.password && (passwordMissing || passwordTooShort) ? (
              <p id="password-error" role="alert" className="mt-1.5 text-xs text-clay">
                {t(
                  language,
                  passwordMissing ? "authPasswordRequired" : "authPasswordTooShort",
                )}
              </p>
            ) : credentialError === "password" ? (
              <p id="password-incorrect-error" role="alert" className="mt-1.5 text-xs text-clay">
                {t(language, "authPasswordIncorrect")}
              </p>
            ) : null}
          </label>

          {mode === "register" ? (
            <>
              {/* Confirm password */}
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">{t(language, "authConfirmPassword")}</span>
                <input
                  required
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => { setConfirmPassword(event.target.value); setFormError(null); }}
                  onBlur={() => touchField("confirmPassword")}
                  placeholder={t(language, "authConfirmPasswordPlaceholder")}
                  aria-invalid={touchedFields.confirmPassword && confirmPasswordInvalid}
                  aria-describedby={
                    touchedFields.confirmPassword && confirmPasswordInvalid
                      ? "confirm-password-error"
                      : undefined
                  }
                  className={`h-11 w-full rounded-xl border bg-paper px-4 text-ink outline-none focus:border-sage-deep ${
                    touchedFields.confirmPassword && confirmPasswordInvalid
                      ? "border-clay"
                      : "border-line"
                  }`}
                  autoComplete="new-password"
                />
                {touchedFields.confirmPassword && confirmPasswordInvalid ? (
                  <p id="confirm-password-error" role="alert" className="mt-1.5 text-xs text-clay">
                    {t(language, "authPasswordMismatch")}
                  </p>
                ) : null}
              </label>

              {/* Nickname */}
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">{t(language, "authNickname")}</span>
                <input
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  onBlur={() => touchField("name")}
                  placeholder={t(language, "authNicknamePlaceholder")}
                  aria-invalid={touchedFields.name && nicknameMissing}
                  aria-describedby={touchedFields.name && nicknameMissing ? "nickname-error" : undefined}
                  className={`h-11 w-full rounded-xl border bg-paper px-4 text-ink outline-none focus:border-sage-deep ${
                    touchedFields.name && nicknameMissing ? "border-clay" : "border-line"
                  }`}
                  autoComplete="name"
                />
                {touchedFields.name && nicknameMissing ? (
                  <p id="nickname-error" role="alert" className="mt-1.5 text-xs text-clay">
                    {t(language, "authNicknameRequired")}
                  </p>
                ) : null}
              </label>

              {/* Country */}
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">{t(language, "authCountry")}</span>
                <select
                  value={country}
                  onChange={(event) => setCountry(event.target.value)}
                  className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-ink outline-none focus:border-sage-deep"
                >
                  <option value="">{t(language, "authCountryPlaceholder")}</option>
                  {COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.label[language] ?? c.label["zh-CN"]}
                    </option>
                  ))}
                </select>
              </label>

              {/* Language */}
              <label className="block">
                <span className="mb-1.5 block text-sm text-ink">{t(language, "selectLanguage")}</span>
                <select
                  disabled
                  value={language}
                  className="h-11 w-full rounded-xl border border-line bg-paper-warm px-4 text-ink-soft outline-none"
                >
                  {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-ink-soft">
                  {t(language, "languageFromHome")}
                </p>
              </label>
            </>
          ) : null}

          {formError ? (
            <p role="alert" className="text-sm text-clay">
              {formError}
            </p>
          ) : error ? (
            <p role="alert" className="text-sm text-clay">
              {t(language, "authRequestFailed")}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="h-12 w-full rounded-full bg-sage-deep font-medium text-paper hover:bg-moss disabled:opacity-60"
          >
            {submitting
              ? t(language, "submitting")
              : mode === "login"
                ? t(language, "authLoginButton")
                : t(language, "authRegisterButton")}
          </button>
        </form>

        {/* Toggle hint */}
        <p className="mt-4 text-center text-sm text-ink-soft">
          {mode === "login" ? (
            <button
              type="button"
              onClick={() => changeMode("register")}
              className="underline transition hover:text-ink"
            >
              {t(language, "authToggleToRegister")}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => changeMode("login")}
              className="underline transition hover:text-ink"
            >
              {t(language, "authToggleToLogin")}
            </button>
          )}
        </p>
      </section>
    </main>
  );
}
