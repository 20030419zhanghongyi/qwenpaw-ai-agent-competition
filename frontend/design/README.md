# Macau StoryWalk — 前端設計方向（Design Direction）

這個資料夾是**設計負責人視角的視覺方向交付**，不是工程程式碼。
它回答一個問題：**澳跡同行憑什麼看上去不像任何一個別人的旅遊 App？**

內容全部基於 [`plan/report ver4.5.docx`](../../plan/)，不虛構景點、不編造數據。

---

## 1. 裡面有什麼

| 檔案 | 是什麼 | 給誰看 |
|---|---|---|
| [`DESIGN_PLAN.md`](./DESIGN_PLAN.md) | 設計計劃書：立場、概念、**Token 系統**（色彩／字體／佈局／動效）、段落地圖、自我批判、與 React 工程的對接 | 設計＋前端，照著實作 |
| [`index.html`](./index.html) | **可直接渲染的概念頁**（單檔、零構建），證明視覺系統成立 | 評委／隊友，雙擊即看 |
| `README.md` | 本檔 | 所有人 |

> ⚠️ 本目錄的 `index.html` **不是** Vite 入口，**不會**覆蓋 [`../index.html`](../index.html)（React 工程入口）。
> 工程任務清單請看 [`../FRONTEND_PLAN.md`](../FRONTEND_PLAN.md)。

---

## 2. 怎麼預覽

```bash
# 任選一種
open frontend/design/index.html                 # macOS，預設瀏覽器開啟
python3 -m http.server 8000 -d frontend/design  # 然後瀏覽器打 http://localhost:8000
```

單檔 HTML，inline CSS + SVG，不需 `npm install`。
字體走 Google Fonts 與 jsDelivr CDN（霞鶩文楷），離線會優雅退回襯線字體。

行動優先：把手機視窗寬度拉到 ≤ 480px 看 mobile；放寬到 ≥ 720px 看石碑並排。

---

## 3. 設計一句話

> **「踩住故事行。」** 把澳門舊區腳下的葡式碎石路（calçada）做成**會說話的介面**——
> 你走過的每一段路，都是一句被解鎖的旁白。

- **簽名元素（只能一個）**：會說話的碎石——Hero 的 SVG 波浪紋 + 「叮」瘋堂斜巷講解石碑；oxblood 朱紅**全頁僅出現在「地點開口」這一刻**。
- **為什麼是深底**：產品是黃昏走街的伴行敘事者，不是旅遊手冊；深底讓望德堂蛋黃、花磚鈷藍、招牌朱紅自帶光地浮起來，也讓「叮」真的像一記打斷。詳見 `DESIGN_PLAN.md §7`。

---

## 4. Token 系統（搬進 React `:root` 即可）

```css
:root{
  --ink:#17120D;        /* 碎石玄武岩 · 頁面地 */
  --limestone:#ECE3D0;  /* 石灰砂漿 · 淺色石碑 */
  --ochre:#D98B2E;      /* 望德堂蛋黃 · 主品牌色 */
  --azulejo:#2E6CA4;    /* 葡式花磚鈷藍 · 次強調 */
  --oxblood:#B23A2B;    /* 屋頂瓦朱 · 僅「叮」 */
  --jade:#5C8C7A;       /* 銅綠／石苔 · 正向狀態 */
}
```

| 字體角色 | 拉丁 | 中文 |
|---|---|---|
| Display 石碑之聲 | Fraunces | LXGW WenKai 霞鶩文楷 |
| Body 故事之聲 | Newsreader | Noto Serif SC |
| UI 控制之聲 | Inter | Noto Sans SC |

---

## 5. 與現有 React 工程的對接（最小步驟）

1. **換 token + 字體**：把 `index.html <style>` 裡的 `:root` 與 `--f-*` 字體棧貼進 [`../src/index.css`](../src/index.css) 的 `:root`，取代現有 `--primary/--accent`。
2. **石碑化現有組件**：
   - `.plaque` → `RouteSummaryCard` / `PoiGuideCard`
   - `.chip` / `.chip.add/.del` → `ReasonChips` / `AdjustmentDiffCard`
   - `.ding` → `TriggerToast`
   - `.node` → `RouteNodeList`
3. **保留雙語眉題系統**：接 [`../src/i18n.ts`](../src/i18n.ts) 的 zh-CN/zh-TW/en/pt 四語字典。
4. 概念頁可作為**視覺基準（visual baseline）**：實作時逐頁對齊它，不另起風格。

> 工程優先級與頁面拆分仍以 [`../FRONTEND_PLAN.md`](../FRONTEND_PLAN.md) 為準（P0 語言/偏好/路線結果 → P1 地圖/調整 → P2 觸發/語音/拍照/明信片）。本設計只決定「長什麼樣」。

---

## 6. 自我批判（節錄，詳見 DESIGN_PLAN §7）

- 深底 ≠ AI 預設「近黑＋酸性單色」：用的是暖玄武岩，搭配從澳門真實立面抽出的層次粉彩，加專屬的波浪碎石母題。
- 雙語眉題＋襯線 ≠ 預設「報紙 hairline」：柔軟石碑、暖深地、波浪分隔，不是零圓角密排專欄。
- 風險辯護：旅遊產品用深底反直覺，但這正是「夜走敘事」的氣質，且讓唯一高光（叮）具備打斷力——**不冒這個險，反而是更大的風險**。

---

## 7. 團隊

**NCLM** — 張弘毅（隊長）· 陳思睿 · 肖懿宣 · 李心然
「千模百煉」AI 開發者系列之學生競賽 · 澳門文旅 · 基於 QwenPaw · 2026.06
