import { NavLink } from "react-router-dom";
import type { LanguageCode } from "@/types";

const COPY = {
  "zh-CN": {
    aria: "个人中心导航",
    profile: "个人资料",
    profileHint: "账户与偏好",
    memoir: "个人回忆录",
    memoirHint: "旅行照片与历史行程",
    postcards: "旅行明信片",
    postcardsHint: "已生成的地点纪念",
  },
  "zh-TW": {
    aria: "個人中心導覽",
    profile: "個人資料",
    profileHint: "帳戶與偏好",
    memoir: "個人回憶錄",
    memoirHint: "旅行照片與歷史行程",
    postcards: "旅行明信片",
    postcardsHint: "已產生的地點紀念",
  },
  en: {
    aria: "Profile navigation",
    profile: "Profile",
    profileHint: "Account and preferences",
    memoir: "Personal memoir",
    memoirHint: "Travel photos and trip history",
    postcards: "Travel postcards",
    postcardsHint: "Keepsakes made at each place",
  },
  pt: {
    aria: "Navegação do perfil",
    profile: "Perfil",
    profileHint: "Conta e preferências",
    memoir: "Memórias pessoais",
    memoirHint: "Fotografias e histórico de viagens",
    postcards: "Postais de viagem",
    postcardsHint: "Recordações criadas em cada local",
  },
} as const;

export function ProfileSidebar({ language }: { language: LanguageCode }) {
  const copy = COPY[language];
  const items = [
    { to: "/profile", label: copy.profile, hint: copy.profileHint, end: true },
    { to: "/profile/memories", label: copy.memoir, hint: copy.memoirHint, end: false },
    { to: "/postcards", label: copy.postcards, hint: copy.postcardsHint, end: false },
  ];

  return (
    <aside className="min-w-0 max-w-full lg:sticky lg:top-20 lg:self-start">
      <nav
        aria-label={copy.aria}
        className="mb-7 flex w-full max-w-full gap-2 overflow-x-auto rounded-2xl border border-line bg-card p-2 shadow-[var(--shadow-soft)] lg:mb-0 lg:block lg:space-y-1"
      >
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              [
                "block min-w-[9.5rem] rounded-xl px-3.5 py-3 transition lg:min-w-0",
                isActive
                  ? "bg-sage-deep text-paper"
                  : "text-ink hover:bg-paper-warm",
              ].join(" ")
            }
          >
            {({ isActive }) => (
              <>
                <span className="block text-sm font-medium">{item.label}</span>
                <span
                  className={`mt-0.5 hidden text-[11px] leading-snug lg:block ${
                    isActive ? "text-paper/75" : "text-ink-soft"
                  }`}
                >
                  {item.hint}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
