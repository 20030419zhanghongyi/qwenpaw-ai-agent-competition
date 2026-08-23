import { useWalk } from "@/state/WalkContext";
import type { LanguageCode } from "@/types";

/**
 * Copy that belongs to the StoryWalk experience rather than the shared travel
 * planner.  Keeping it here makes a story package reviewable by the content
 * team without growing the general UI dictionary with story-only keys.
 *
 * The English and Portuguese copy is intentionally adapted for visitors, not
 * translated word-for-word. Traditional Chinese follows Macau written usage.
 */
const COPY = {
  "zh-CN": {
    back: "返回",
    loadingStory: "正在展开旧地图…",
    loadingRoute: "正在恢复故事路线…",
    loadingChapter: "正在恢复当前章节…",
    storyUnavailable: "故事暂未开放",
    backToPreferences: "← 返回偏好页",
    limitedWalk: "Story Walk · 限定故事游",
    estimatedHours: "约 {hours} 小时",
    realPlaces: "六个真实地点",
    fieldPuzzles: "五个现场谜题",
    puzzlesSkippable: "谜题均可跳过",
    safetyTitle: "安全游览说明",
    safety1: "请在开放区域游览，不进入封闭或施工区域。",
    safety2: "不需要触碰文物，也不以 GPS 作为强制通关条件。",
    safety3: "现场环境变化时，以安全和官方开放安排为先。",
    contentBoundary: "史实与剧情边界",
    loginToStart: "登录并开始",
    viewRecord: "查看完成记录",
    resume: "继续上次进度",
    startStory: "开始故事",
    preparing: "正在准备故事…",
    resumeHint: "会从服务端保存的最新章节继续",
    routeEyebrow: "莲城路线",
    currentMission: "当前任务",
    loadingChapterTitle: "载入当前章节",
    unlockRoute: "先完成序章，开启六站路线",
    secretNotes: "五张密笺",
    petalsServer: "花瓣仅在服务端发放奖励后点亮",
    cityMaps: "城市双图",
    incompleteNotes: "尚未集齐的密笺",
    sixStops: "一日六站",
    timeline: "章节时间线",
    currentStop: "当前站 · 点击进入",
    skipped: "已完成 · 谜题已跳过",
    completed: "已完成 · 查看回顾",
    locked: "尚未解锁",
    finishPrevious: "完成前一站后解锁",
    viewMap: "查看六站地图",
    enterChapter: "进入当前章节",
    chapter: "第 {order} 站 / 6",
    prologue: "序章",
    landscapeHint: "建议旋转回竖屏，获得更完整的故事体验。",
    location: "地点：{name}",
    arrivalCheck: "到达确认",
    arrivalSafety: "请只在开放、安全的区域确认到达。不需要进入封闭区域，不需要触碰文物，也不强制使用 GPS。",
    routeOpened: "路线已开启",
    chapterCompleted: "章节完成",
    progressSaved: "进度已经保存",
    progressKeeps: "当前章节内容会保持到你主动查看下一站，不会被新的章节瞬间替换。",
    scene: "场景",
    observations: "现场观察与线索",
    knowledgeCards: "知识卡",
    puzzleQuestion: "阿澜留下的问题",
    combineMaps: "让两张图互相说明",
    combineMapsBody: "调整透明度，让城市双图与今天的澳门叠在一起。这个动作只承担叙事体验，不作为接口答案。",
    opacity: "双图透明度：{value}%",
    holdOverlay: "按住让双图重合",
    petalsComplete: "五站留下的纹理彼此补全，组成同一朵市花。",
    arrived: "我已到达",
    confirmingArrival: "正在确认到达…",
    arrivalHint: "请先确认周围环境安全",
    goToAmaze: "去第一站：妈阁庙",
    writeNote: "写下今日补记",
    ending: "最终章",
    journeyComplete: "旅程完成",
    noteToday: "今日补记",
    leaveReader: "留给下一位读者",
    noteHeading: "把今天看到的澳门，留给下一位读者",
    noteBody: "不必重画整座城市。写下你在什么时间来到这里、看见了什么，以及今天仍值得继续查证的部分。",
    noteOptional: "今日补记（可选）",
    notePlaceholder: "例如：今天的城市仍然不是澳门的全部……",
    saveNote: "正在保存补记…",
    finishNote: "完成今日补记",
    returnPlanner: "返回普通旅行规划",
    recap: "章节回顾",
    storyDialogue: "故事对话",
    dialogue: "对话 {current}/{total}",
    showHistory: "查看历史对话",
    hideHistory: "收起历史",
    swipeHistory: "向上划可回看历史对话",
    previousPanel: "上一格",
    nextPanel: "阅读下一格",
    enterDialogue: "进入对话",
    swipePages: "可左右滑动翻页",
    askAlian: "问阿莲",
    agentTitle: "随行问答",
    ask: "问{persona}",
    close: "关闭",
    agentIntro: "可以问我当前地点、公开历史或已经出现的剧情。我不会提前透露谜题答案。",
    suggested: "你可以这样问",
    thinking: "阿莲正在查找资料…",
    hint: "提示",
    skip: "跳过",
    attemptCount: "已尝试 {count} 次",
    aliansHint: "阿莲的提示",
  },
  "zh-TW": {
    back: "返回", loadingStory: "正在展開舊地圖…", loadingRoute: "正在恢復故事路線…", loadingChapter: "正在恢復目前章節…", storyUnavailable: "故事暫未開放", backToPreferences: "← 返回偏好設定", limitedWalk: "Story Walk · 限定故事遊", estimatedHours: "約 {hours} 小時", realPlaces: "六個真實地點", fieldPuzzles: "五個現場謎題", puzzlesSkippable: "謎題均可略過", safetyTitle: "安全遊覽說明", safety1: "請在開放區域遊覽，切勿進入封閉或施工區域。", safety2: "毋須觸碰文物，亦不會以 GPS 作為強制通關條件。", safety3: "現場環境如有變化，請以安全及官方開放安排為先。", contentBoundary: "史實與劇情界線", loginToStart: "登入並開始", viewRecord: "查看完成紀錄", resume: "繼續上次進度", startStory: "開始故事", preparing: "正在準備故事…", resumeHint: "將從伺服器儲存的最新章節繼續", routeEyebrow: "蓮城路線", currentMission: "目前任務", loadingChapterTitle: "正在載入章節", unlockRoute: "先完成序章，開啟六站路線", secretNotes: "五張密箋", petalsServer: "花瓣只會在伺服器發放獎勵後亮起", cityMaps: "城市雙圖", incompleteNotes: "尚未集齊的密箋", sixStops: "一日六站", timeline: "章節時間線", currentStop: "目前站 · 點選進入", skipped: "已完成 · 已略過謎題", completed: "已完成 · 查看回顧", locked: "尚未解鎖", finishPrevious: "完成前一站後解鎖", viewMap: "查看六站地圖", enterChapter: "進入目前章節", chapter: "第 {order} 站 / 6", prologue: "序章", landscapeHint: "建議轉回直向畫面，以獲得更完整的故事體驗。", location: "地點：{name}", arrivalCheck: "到達確認", arrivalSafety: "請只在開放且安全的區域確認到達。毋須進入封閉區域、觸碰文物或強制使用 GPS。", routeOpened: "路線已開啟", chapterCompleted: "章節完成", progressSaved: "進度已儲存", progressKeeps: "在你主動查看下一站前，目前章節內容會保留，不會立即被新章節取代。", scene: "場景", observations: "現場觀察與線索", knowledgeCards: "知識卡", puzzleQuestion: "阿瀾留下的問題", combineMaps: "讓兩張圖互相說明", combineMapsBody: "調整透明度，讓城市雙圖與今日澳門疊合。此操作只服務於敘事體驗，並非答題條件。", opacity: "雙圖透明度：{value}%", holdOverlay: "按住讓雙圖重合", petalsComplete: "五站留下的紋理彼此補全，組成同一朵市花。", arrived: "我已到達", confirmingArrival: "正在確認到達…", arrivalHint: "請先確認周遭環境安全", goToAmaze: "前往第一站：媽閣廟", writeNote: "寫下今日補記", ending: "最終章", journeyComplete: "旅程完成", noteToday: "今日補記", leaveReader: "留給下一位讀者", noteHeading: "把今天看見的澳門，留給下一位讀者", noteBody: "毋須重畫整座城市。寫下你何時來到這裡、看見了甚麼，以及今天仍值得繼續查證的部分。", noteOptional: "今日補記（可選）", notePlaceholder: "例如：今天的城市仍然不是澳門的全部……", saveNote: "正在儲存補記…", finishNote: "完成今日補記", returnPlanner: "返回一般行程規劃", recap: "章節回顧", storyDialogue: "故事對話", dialogue: "對話 {current}/{total}", showHistory: "查看歷史對話", hideHistory: "收起歷史", swipeHistory: "向上滑動可回看歷史對話", previousPanel: "上一格", nextPanel: "閱讀下一格", enterDialogue: "進入對話", swipePages: "可左右滑動翻頁", askAlian: "問阿蓮", agentTitle: "隨行問答", ask: "問{persona}", close: "關閉", agentIntro: "你可問我目前地點、公開歷史或已出現的劇情。我不會預先透露謎題答案。", suggested: "你可以這樣問", thinking: "阿蓮正在查找資料…", hint: "提示", skip: "略過", attemptCount: "已嘗試 {count} 次", aliansHint: "阿蓮的提示" },
  en: {
    back: "Back", loadingStory: "Unfolding the old map…", loadingRoute: "Restoring the story route…", loadingChapter: "Restoring this chapter…", storyUnavailable: "This story is not available yet", backToPreferences: "← Back to preferences", limitedWalk: "Story Walk · Limited journey", estimatedHours: "About {hours} hours", realPlaces: "Six real places", fieldPuzzles: "Five on-site puzzles", puzzlesSkippable: "Every puzzle may be skipped", safetyTitle: "Visit safely", safety1: "Stay in publicly open areas; do not enter closed or construction zones.", safety2: "There is no need to touch heritage objects or use GPS to progress.", safety3: "If conditions change, follow safety guidance and official opening arrangements.", contentBoundary: "History and fictional narrative", loginToStart: "Sign in to begin", viewRecord: "View completed journey", resume: "Resume journey", startStory: "Begin story", preparing: "Preparing the story…", resumeHint: "You will resume from the latest chapter saved on the server", routeEyebrow: "Lotus City route", currentMission: "Current mission", loadingChapterTitle: "Loading current chapter", unlockRoute: "Complete the prologue to unlock the six-stop route", secretNotes: "Five secret notes", petalsServer: "Petals light up only after the server grants a reward", cityMaps: "Two city maps", incompleteNotes: "Notes not yet complete", sixStops: "Six stops, one day", timeline: "Chapter timeline", currentStop: "Current stop · tap to enter", skipped: "Complete · puzzle skipped", completed: "Complete · view recap", locked: "Not yet unlocked", finishPrevious: "Complete the previous stop to unlock", viewMap: "View six-stop map", enterChapter: "Enter current chapter", chapter: "Stop {order} of 6", prologue: "Prologue", landscapeHint: "For the full story experience, please turn your device upright.", location: "Place: {name}", arrivalCheck: "Arrival check", arrivalSafety: "Confirm arrival only from an open, safe area. Do not enter closed areas, touch heritage objects, or rely on GPS.", routeOpened: "Route opened", chapterCompleted: "Chapter complete", progressSaved: "Progress saved", progressKeeps: "This chapter remains here until you choose the next stop, so the new chapter will not replace it abruptly.", scene: "Scene", observations: "Things to notice", knowledgeCards: "Knowledge cards", puzzleQuestion: "A Lan’s question", combineMaps: "Let the two maps explain each other", combineMapsBody: "Adjust the transparency to layer the two city maps over Macau today. This is part of the story, not an answer check.", opacity: "Map transparency: {value}%", holdOverlay: "Hold to align the two maps", petalsComplete: "The textures gathered at five stops complete one city flower.", arrived: "I have arrived", confirmingArrival: "Confirming arrival…", arrivalHint: "Please check that your surroundings are safe first", goToAmaze: "Go to stop 1: A-Ma Temple", writeNote: "Write today’s note", ending: "Final chapter", journeyComplete: "Journey complete", noteToday: "Today’s note", leaveReader: "For the next reader", noteHeading: "Leave today’s Macau for the next reader", noteBody: "You do not need to redraw the city. Note when you were here, what you saw, and what still deserves to be checked.", noteOptional: "Today’s note (optional)", notePlaceholder: "For example: today’s city is still not the whole of Macau…", saveNote: "Saving your note…", finishNote: "Complete today’s note", returnPlanner: "Return to travel planning", recap: "Chapter recap", storyDialogue: "Story dialogue", dialogue: "Dialogue {current}/{total}", showHistory: "Show dialogue history", hideHistory: "Hide history", swipeHistory: "Swipe up to revisit earlier dialogue", previousPanel: "Previous panel", nextPanel: "Next panel", enterDialogue: "Enter dialogue", swipePages: "Swipe left or right to turn pages", askAlian: "Ask A Lin", agentTitle: "Ask along the way", ask: "Ask {persona}", close: "Close", agentIntro: "Ask about this place, public history, or scenes already revealed. I will not disclose puzzle answers early.", suggested: "Try asking", thinking: "A Lin is checking the sources…", hint: "Hint", skip: "Skip", attemptCount: "Attempts: {count}", aliansHint: "A Lin’s hint" },
  pt: {
    back: "Voltar", loadingStory: "A abrir o mapa antigo…", loadingRoute: "A restaurar o percurso da história…", loadingChapter: "A restaurar este capítulo…", storyUnavailable: "Esta história ainda não está disponível", backToPreferences: "← Voltar às preferências", limitedWalk: "Story Walk · Percurso especial", estimatedHours: "Cerca de {hours} horas", realPlaces: "Seis lugares reais", fieldPuzzles: "Cinco enigmas no local", puzzlesSkippable: "Todos os enigmas podem ser saltados", safetyTitle: "Visite em segurança", safety1: "Permaneça em zonas abertas ao público; não entre em áreas vedadas ou em obras.", safety2: "Não é preciso tocar no património nem usar GPS para avançar.", safety3: "Se as condições mudarem, siga a segurança e os horários oficiais.", contentBoundary: "História e ficção", loginToStart: "Iniciar sessão para começar", viewRecord: "Ver percurso concluído", resume: "Retomar percurso", startStory: "Começar a história", preparing: "A preparar a história…", resumeHint: "Retomará no último capítulo guardado no servidor", routeEyebrow: "Rota da Cidade de Lótus", currentMission: "Missão atual", loadingChapterTitle: "A carregar o capítulo", unlockRoute: "Conclua o prólogo para desbloquear as seis paragens", secretNotes: "Cinco bilhetes secretos", petalsServer: "As pétalas só se acendem quando o servidor atribui a recompensa", cityMaps: "Dois mapas da cidade", incompleteNotes: "Bilhetes ainda incompletos", sixStops: "Seis paragens num dia", timeline: "Linha do tempo", currentStop: "Paragem atual · toque para entrar", skipped: "Concluído · enigma saltado", completed: "Concluído · ver resumo", locked: "Ainda bloqueado", finishPrevious: "Conclua a paragem anterior para desbloquear", viewMap: "Ver mapa das seis paragens", enterChapter: "Entrar no capítulo atual", chapter: "Paragem {order} de 6", prologue: "Prólogo", landscapeHint: "Para a experiência completa, rode o dispositivo para a vertical.", location: "Local: {name}", arrivalCheck: "Confirmação de chegada", arrivalSafety: "Confirme a chegada apenas numa zona aberta e segura. Não entre em áreas vedadas, não toque no património e não dependa de GPS.", routeOpened: "Percurso aberto", chapterCompleted: "Capítulo concluído", progressSaved: "Progresso guardado", progressKeeps: "Este capítulo fica disponível até escolher a próxima paragem; o novo não o substituirá de imediato.", scene: "Cena", observations: "Observações e pistas", knowledgeCards: "Cartões de conhecimento", puzzleQuestion: "A pergunta deixada por A Lan", combineMaps: "Deixe os dois mapas explicarem-se", combineMapsBody: "Ajuste a transparência para sobrepor os dois mapas da cidade à Macau de hoje. É uma experiência narrativa, não uma resposta avaliada.", opacity: "Transparência do mapa: {value}%", holdOverlay: "Mantenha premido para alinhar os mapas", petalsComplete: "As texturas recolhidas em cinco paragens completam uma só flor da cidade.", arrived: "Já cheguei", confirmingArrival: "A confirmar a chegada…", arrivalHint: "Verifique primeiro se o local à sua volta é seguro", goToAmaze: "Ir à 1.ª paragem: Templo de A-Má", writeNote: "Escrever a nota de hoje", ending: "Capítulo final", journeyComplete: "Percurso concluído", noteToday: "Nota de hoje", leaveReader: "Para o próximo leitor", noteHeading: "Deixe a Macau de hoje para o próximo leitor", noteBody: "Não precisa de redesenhar a cidade inteira. Registe quando esteve aqui, o que viu e o que ainda merece ser verificado.", noteOptional: "Nota de hoje (opcional)", notePlaceholder: "Por exemplo: a cidade de hoje ainda não é toda a Macau…", saveNote: "A guardar a nota…", finishNote: "Concluir a nota de hoje", returnPlanner: "Voltar ao planeamento da viagem", recap: "Resumo do capítulo", storyDialogue: "Diálogo da história", dialogue: "Diálogo {current}/{total}", showHistory: "Ver histórico", hideHistory: "Ocultar histórico", swipeHistory: "Deslize para cima para rever o diálogo", previousPanel: "Painel anterior", nextPanel: "Painel seguinte", enterDialogue: "Entrar no diálogo", swipePages: "Deslize para virar as páginas", askAlian: "Perguntar a A Lin", agentTitle: "Perguntas pelo caminho", ask: "Perguntar a {persona}", close: "Fechar", agentIntro: "Pode perguntar sobre este local, história pública ou cenas já reveladas. Não vou antecipar respostas dos enigmas.", suggested: "Experimente perguntar", thinking: "A Lin está a consultar fontes…", hint: "Pista", skip: "Saltar", attemptCount: "Tentativas: {count}", aliansHint: "Pista de A Lin" },
} as const;

export type StoryMessageKey = keyof typeof COPY["zh-CN"];

export function storyT(
  language: LanguageCode,
  key: StoryMessageKey,
  values: Record<string, string | number> = {},
): string {
  return COPY[language][key].replace(/\{(\w+)\}/g, (_, name: string) =>
    String(values[name] ?? `{${name}}`),
  );
}

export function useStoryMessages() {
  const { language } = useWalk();
  return (key: StoryMessageKey, values?: Record<string, string | number>) =>
    storyT(language, key, values);
}
