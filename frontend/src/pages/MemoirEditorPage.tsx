import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  createMemoirShare,
  deleteMemoirPhoto,
  getMemoir,
  loadPrivatePhoto,
  revokeMemoirShare,
  updateMemoir,
  uploadMemoirPhoto,
  type MemoirStyle,
  type SharePrivacy,
  type TravelMemoir,
} from "@/api/memoirs";
import { postcardImageSrc } from "@/api/postcards";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import {
  localizedMemoirChapterBody,
  localizedMemoirClosing,
  localizedMemoirIntroduction,
  localizedMemoirTitle,
} from "@/lib/memoirLocalization";
import { localizedPoiIdName } from "@/lib/poiLocalization";
import { useAuth } from "@/state/AuthContext";
import { useWalk } from "@/state/WalkContext";

const COPY = {
  "zh-CN": { back: "返回个人中心", eyebrow: "个人旅行回忆录", complete: "完成编辑", draftStatus: "草稿 · 自动保存", completedStatus: "编辑已完成", saving: "正在保存…", saved: "所有修改已保存", title: "回忆录标题", intro: "序言", closing: "旅行结语", style: "叙事风格", diary: "温柔日记", magazine: "旅行杂志", social: "轻松短句", documentary: "纪录片旁白", chapters: "旅行章节", body: "章节叙述", note: "我的补记", include: "收入回忆录", photos: "真实照片", upload: "上传照片", location: "关联地点", people: "照片中有人物", peopleHint: "人物照片在分享时默认隐藏；原图不会被修改。", cover: "设为封面", coverNow: "当前封面", remove: "删除", share: "分享与隐私", makeShare: "生成新的分享链接", revoke: "撤销分享链接", copied: "分享链接已复制", hidePeople: "隐藏人物照片", hideDate: "隐藏旅行日期", hideRoute: "隐藏精确路线", hideNotes: "隐藏个人补记", private: "回忆录默认私密。只有主动生成链接后，别人才能查看隐私裁剪后的版本。", noPhoto: "还没有上传真实照片。", login: "请先登录后编辑回忆录。", ongoing: "旅途中记录", finished: "旅程已完成" },
  "zh-TW": { back: "返回個人中心", eyebrow: "個人旅行回憶錄", complete: "完成編輯", draftStatus: "草稿 · 自動儲存", completedStatus: "編輯已完成", saving: "正在儲存…", saved: "所有修改已儲存", title: "回憶錄標題", intro: "序言", closing: "旅行結語", style: "敘事風格", diary: "溫柔日記", magazine: "旅行雜誌", social: "輕鬆短句", documentary: "紀錄片旁白", chapters: "旅行章節", body: "章節敘述", note: "我的補記", include: "收入回憶錄", photos: "真實照片", upload: "上傳照片", location: "關聯地點", people: "照片中有人物", peopleHint: "人物照片在分享時預設隱藏；原圖不會被修改。", cover: "設為封面", coverNow: "目前封面", remove: "刪除", share: "分享與隱私", makeShare: "產生新的分享連結", revoke: "撤銷分享連結", copied: "分享連結已複製", hidePeople: "隱藏人物照片", hideDate: "隱藏旅行日期", hideRoute: "隱藏精確路線", hideNotes: "隱藏個人補記", private: "回憶錄預設私密。只有主動產生連結後，別人才能查看隱私裁剪後的版本。", noPhoto: "還沒有上傳真實照片。", login: "請先登入後編輯回憶錄。", ongoing: "旅途中記錄", finished: "旅程已完成" },
  en: { back: "Back to profile", eyebrow: "Personal travel memoir", complete: "Finish editing", draftStatus: "Draft · autosaved", completedStatus: "Editing complete", saving: "Saving…", saved: "All changes saved", title: "Memoir title", intro: "Introduction", closing: "Closing", style: "Narrative style", diary: "Gentle diary", magazine: "Travel magazine", social: "Short and light", documentary: "Documentary", chapters: "Trip chapters", body: "Chapter narrative", note: "My note", include: "Include in memoir", photos: "Real photos", upload: "Upload photo", location: "Related place", people: "People appear in this photo", peopleHint: "People photos are hidden from sharing by default. Originals are never altered.", cover: "Use as cover", coverNow: "Current cover", remove: "Delete", share: "Sharing and privacy", makeShare: "Generate a new share link", revoke: "Revoke share link", copied: "Share link copied", hidePeople: "Hide people photos", hideDate: "Hide trip date", hideRoute: "Hide exact route", hideNotes: "Hide personal notes", private: "Memoirs are private by default. Others can only see a privacy-filtered version after you create a link.", noPhoto: "No real photos uploaded yet.", login: "Sign in to edit this memoir.", ongoing: "Recorded during the trip", finished: "Trip completed" },
  pt: { back: "Voltar ao perfil", eyebrow: "Memórias pessoais", complete: "Concluir edição", draftStatus: "Rascunho · guardado automaticamente", completedStatus: "Edição concluída", saving: "A guardar…", saved: "Todas as alterações foram guardadas", title: "Título", intro: "Introdução", closing: "Conclusão", style: "Estilo narrativo", diary: "Diário suave", magazine: "Revista de viagem", social: "Frases leves", documentary: "Documentário", chapters: "Capítulos", body: "Narrativa", note: "A minha nota", include: "Incluir", photos: "Fotografias reais", upload: "Carregar fotografia", location: "Local associado", people: "Há pessoas nesta fotografia", peopleHint: "As fotografias com pessoas ficam ocultas por predefinição. O original nunca é alterado.", cover: "Usar como capa", coverNow: "Capa atual", remove: "Eliminar", share: "Partilha e privacidade", makeShare: "Gerar nova ligação", revoke: "Revogar ligação", copied: "Ligação copiada", hidePeople: "Ocultar fotografias com pessoas", hideDate: "Ocultar data", hideRoute: "Ocultar percurso exato", hideNotes: "Ocultar notas pessoais", private: "As memórias são privadas por predefinição e só são partilhadas após criar uma ligação.", noPhoto: "Ainda não há fotografias.", login: "Inicie sessão para editar.", ongoing: "Registo durante a viagem", finished: "Viagem concluída" },
} as const;

const STYLES: MemoirStyle[] = ["diary", "magazine", "social", "documentary"];

function editableMemoir(memoir: TravelMemoir) {
  return JSON.stringify({
    title: memoir.title,
    style: memoir.style,
    introduction: memoir.introduction,
    closing: memoir.closing,
    status: memoir.status,
    cover_photo_id: memoir.cover_photo_id,
    chapters: memoir.chapters,
  });
}

export function MemoirEditorPage() {
  const { memoirId = "" } = useParams();
  const navigate = useNavigate();
  const { token, isAuthenticated } = useAuth();
  const { language } = useWalk();
  const copy = COPY[language];
  const [memoir, setMemoir] = useState<TravelMemoir | null>(null);
  const [photoUrls, setPhotoUrls] = useState<Record<string, string>>({});
  const [photoPoi, setPhotoPoi] = useState("");
  const [hasPeople, setHasPeople] = useState(false);
  const [busy, setBusy] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);
  const [privacy, setPrivacy] = useState<SharePrivacy>({ hide_people_photos: true, hide_date: false, hide_exact_route: false, hide_personal_notes: false });
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const lastSavedMemoir = useRef<string | null>(null);
  const saveRevision = useRef(0);
  const autosaveTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!token || !memoirId) return;
    void getMemoir(memoirId, token).then((loaded) => {
      lastSavedMemoir.current = editableMemoir(loaded);
      setMemoir(loaded);
    }).catch((err: unknown) => setError(err instanceof Error ? err.message : "Unable to load memoir"));
  }, [memoirId, token]);

  useEffect(() => {
    if (!memoir || !token) return;
    const snapshot = editableMemoir(memoir);
    if (lastSavedMemoir.current === snapshot) return;
    if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current);
    const revision = ++saveRevision.current;
    setSaveState("saving");
    autosaveTimer.current = window.setTimeout(() => {
      void updateMemoir(memoir.memoir_id, memoir, token)
        .then((savedMemoir) => {
          if (revision !== saveRevision.current) return;
          lastSavedMemoir.current = editableMemoir(savedMemoir);
          setMemoir(savedMemoir);
          setSaveState("saved");
        })
        .catch((saveError: unknown) => {
          if (revision !== saveRevision.current) return;
          setError(saveError instanceof Error ? saveError.message : "Unable to save");
          setSaveState("idle");
        });
    }, 800);
    return () => {
      if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current);
    };
  }, [memoir, token]);

  useEffect(() => {
    if (!memoir || !token) return;
    let cancelled = false;
    const created: string[] = [];
    void Promise.all(memoir.photos.map(async (photo) => [photo.photo_id, await loadPrivatePhoto(photo, memoir.memoir_id, token)] as const)).then((entries) => {
      if (cancelled) { entries.forEach(([, url]) => URL.revokeObjectURL(url)); return; }
      entries.forEach(([, url]) => created.push(url));
      setPhotoUrls(Object.fromEntries(entries));
    });
    return () => { cancelled = true; created.forEach((url) => URL.revokeObjectURL(url)); };
  }, [memoir?.memoir_id, memoir?.photos, token]);

  const coverUrl = memoir?.cover_photo_id ? photoUrls[memoir.cover_photo_id] : undefined;
  const updateChapter = (index: number, values: Partial<TravelMemoir["chapters"][number]>) => setMemoir((current) => current ? ({ ...current, chapters: current.chapters.map((chapter, i) => i === index ? { ...chapter, ...values } : chapter) }) : current);
  const finishEditing = async () => {
    if (!memoir || !token) return;
    if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current);
    ++saveRevision.current;
    setBusy(true); setError(null);
    try {
      const savedMemoir = await updateMemoir(memoir.memoir_id, { ...memoir, status: "completed" }, token);
      lastSavedMemoir.current = editableMemoir(savedMemoir);
      setMemoir(savedMemoir);
      setSaveState("saved");
    }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to save"); }
    finally { setBusy(false); }
  };
  const upload = async (file: File | undefined) => {
    if (!file || !memoir || !token) return;
    setBusy(true); setError(null);
    try { await uploadMemoirPhoto(memoir.memoir_id, file, photoPoi || null, hasPeople, token); setMemoir(await getMemoir(memoir.memoir_id, token)); setHasPeople(false); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to upload"); }
    finally { setBusy(false); }
  };
  const makeShare = async () => {
    if (!memoir || !token) return;
    setBusy(true); setError(null);
    try { const result = await createMemoirShare(memoir.memoir_id, privacy, token); const absolute = new URL(result.share_url, window.location.origin).toString(); setShareUrl(absolute); await navigator.clipboard.writeText(absolute).catch(() => undefined); setMemoir({ ...memoir, active_share_token: result.token }); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to share"); }
    finally { setBusy(false); }
  };
  const revoke = async () => { if (!memoir || !token) return; await revokeMemoirShare(memoir.memoir_id, token); setMemoir({ ...memoir, active_share_token: null }); setShareUrl(null); };
  const associatedPhotos = useMemo(() => {
    const result: Record<string, TravelMemoir["photos"]> = {};
    for (const photo of memoir?.photos ?? []) {
      (result[photo.poi_id ?? "unassigned"] ??= []).push(photo);
    }
    return result;
  }, [memoir?.photos]);
  const chapterName = (chapter: TravelMemoir["chapters"][number]) =>
    localizedPoiIdName(chapter.poi_id, language, chapter.poi_name);

  if (!isAuthenticated) return <main className="mx-auto max-w-3xl flex-1 px-5 py-12"><p>{copy.login}</p><Link to="/auth" className="mt-4 inline-block text-sage-deep underline">Login</Link></main>;
  if (error && !memoir) return <main className="mx-auto max-w-3xl flex-1 px-5 py-12"><ErrorState title="Error" message={error} onRetry={() => navigate("/profile")} retryLabel={copy.back} /></main>;
  if (!memoir) return <main className="mx-auto max-w-3xl flex-1 px-5 py-12"><LoadingState label="Loading memoir…" /></main>;

  return <main className="relative flex-1 bg-paper pb-24"><div className="mx-auto max-w-3xl px-5 pt-8 lg:px-0">
    <Link to="/profile" className="text-sm text-ink-soft">← {copy.back}</Link>
    <div className="mt-6 overflow-hidden rounded-[2rem] border border-line bg-card shadow-[var(--shadow-soft)]">{coverUrl ? <img src={coverUrl} alt="" className="h-64 w-full object-cover" /> : <div className="h-40 bg-gradient-to-br from-sage-deep/20 via-paper-warm to-clay/10" />}<div className="p-6"><p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sage-deep">{copy.eyebrow} · {memoir.trip_status === "completed" ? copy.finished : copy.ongoing}</p><input aria-label={copy.title} value={localizedMemoirTitle(memoir.title, language)} onChange={(e) => setMemoir({ ...memoir, title: e.target.value })} className="mt-3 w-full border-0 bg-transparent font-display text-3xl text-ink outline-none" /><p className="mt-2 text-xs text-ink-soft">{memoir.travel_date ? new Date(memoir.travel_date).toLocaleDateString(language) : ""}</p></div></div>
    <AzulejoBand className="my-8" />
    {error ? <p className="mb-5 rounded-xl bg-clay/10 p-3 text-sm text-clay">{error}</p> : null}
    <section className="rounded-2xl border border-line bg-card p-5"><label className="text-xs font-semibold uppercase tracking-[0.16em] text-sage-deep">{copy.style}</label><div className="mt-3 flex flex-wrap gap-2">{STYLES.map((style) => <button key={style} type="button" onClick={() => setMemoir({ ...memoir, style })} className={`rounded-full border px-4 py-2 text-sm ${memoir.style === style ? "border-sage-deep bg-sage-deep text-paper" : "border-line text-ink"}`}>{copy[style]}</button>)}</div><label className="mt-5 block text-sm text-ink">{copy.intro}<textarea value={localizedMemoirIntroduction(memoir.introduction, language)} onChange={(e) => setMemoir({ ...memoir, introduction: e.target.value })} rows={3} className="mt-2 w-full rounded-xl border border-line bg-paper p-3" /></label></section>
    <section className="mt-8"><h2 className="font-display text-2xl text-ink">{copy.chapters}</h2><div className="mt-4 space-y-5">{memoir.chapters.map((chapter, index) => <article key={chapter.poi_id} className={`rounded-2xl border p-5 ${chapter.included ? "border-line bg-card" : "border-line bg-card/50 opacity-70"}`}><div className="flex items-start justify-between gap-3"><div><p className="text-xs text-sage-deep">{index + 1}</p><h3 className="font-display text-xl text-ink">{chapterName(chapter)}</h3></div><label className="flex items-center gap-2 text-xs text-ink-soft"><input type="checkbox" checked={chapter.included} onChange={(e) => updateChapter(index, { included: e.target.checked })} />{copy.include}</label></div>{chapter.postcard_image_url ? <img src={postcardImageSrc(chapter.postcard_image_url)} alt="" className="mt-4 max-h-64 w-full rounded-xl object-cover" /> : null}<label className="mt-4 block text-xs text-ink-soft">{copy.body}<textarea value={localizedMemoirChapterBody(chapter.body, memoir.style, index + 1, chapterName(chapter), language)} onChange={(e) => updateChapter(index, { body: e.target.value })} rows={3} className="mt-2 w-full rounded-xl border border-line bg-paper p-3 text-sm text-ink" /></label><label className="mt-3 block text-xs text-ink-soft">{copy.note}<textarea value={chapter.personal_note} onChange={(e) => updateChapter(index, { personal_note: e.target.value })} rows={2} className="mt-2 w-full rounded-xl border border-line bg-paper p-3 text-sm text-ink" /></label>{(associatedPhotos[chapter.poi_id] ?? []).map((photo) => photoUrls[photo.photo_id] ? <img key={photo.photo_id} src={photoUrls[photo.photo_id]} alt="" className="mt-3 h-40 w-full rounded-xl object-cover" /> : null)}</article>)}</div></section>
    <section className="mt-8 rounded-2xl border border-line bg-card p-5"><h2 className="font-display text-2xl text-ink">{copy.photos}</h2><p className="mt-1 text-xs text-ink-soft">{copy.peopleHint}</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><select value={photoPoi} onChange={(e) => setPhotoPoi(e.target.value)} className="rounded-xl border border-line bg-paper px-3 py-2 text-sm"><option value="">{copy.location}</option>{memoir.chapters.map((chapter) => <option key={chapter.poi_id} value={chapter.poi_id}>{chapterName(chapter)}</option>)}</select><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={hasPeople} onChange={(e) => setHasPeople(e.target.checked)} />{copy.people}</label><label className="inline-flex cursor-pointer items-center justify-center rounded-full bg-sage-deep px-5 py-2.5 text-sm text-paper"><input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={(e) => void upload(e.target.files?.[0])} className="sr-only" />{copy.upload}</label></div>{memoir.photos.length === 0 ? <p className="mt-5 text-sm text-ink-soft">{copy.noPhoto}</p> : <div className="mt-5 grid gap-4 sm:grid-cols-2">{memoir.photos.map((photo) => <div key={photo.photo_id} className="overflow-hidden rounded-xl border border-line">{photoUrls[photo.photo_id] ? <img src={photoUrls[photo.photo_id]} alt="" className="h-40 w-full object-cover" /> : null}<div className="flex flex-wrap gap-3 p-3 text-xs"><button type="button" onClick={() => setMemoir({ ...memoir, cover_photo_id: photo.photo_id })} className="text-sage-deep">{memoir.cover_photo_id === photo.photo_id ? copy.coverNow : copy.cover}</button><button type="button" onClick={async () => { if (!token) return; await deleteMemoirPhoto(memoir.memoir_id, photo.photo_id, token); setMemoir(await getMemoir(memoir.memoir_id, token)); }} className="text-clay">{copy.remove}</button>{photo.has_people ? <span className="text-ink-soft">{copy.people}</span> : null}</div></div>)}</div>}</section>
    <section className="mt-8 rounded-2xl border border-line bg-card p-5"><label className="block text-sm text-ink">{copy.closing}<textarea value={localizedMemoirClosing(memoir.closing, language)} onChange={(e) => setMemoir({ ...memoir, closing: e.target.value })} rows={3} className="mt-2 w-full rounded-xl border border-line bg-paper p-3" /></label></section>
    <section className="mt-8 rounded-2xl border border-sage-deep/20 bg-paper-warm p-5"><h2 className="font-display text-2xl text-ink">{copy.share}</h2><p className="mt-2 text-sm text-ink-soft">{copy.private}</p><div className="mt-4 grid gap-3 sm:grid-cols-2">{([['hide_people_photos', copy.hidePeople], ['hide_date', copy.hideDate], ['hide_exact_route', copy.hideRoute], ['hide_personal_notes', copy.hideNotes]] as Array<[keyof SharePrivacy, string]>).map(([key, label]) => <label key={key} className="flex items-center gap-2 text-sm text-ink"><input type="checkbox" checked={privacy[key]} onChange={(e) => setPrivacy({ ...privacy, [key]: e.target.checked })} />{label}</label>)}</div><div className="mt-5 flex flex-wrap gap-3"><button type="button" disabled={busy} onClick={() => void makeShare()} className="rounded-full bg-sage-deep px-5 py-2.5 text-sm text-paper">{copy.makeShare}</button>{memoir.active_share_token ? <button type="button" onClick={() => void revoke()} className="rounded-full border border-clay px-5 py-2.5 text-sm text-clay">{copy.revoke}</button> : null}</div>{shareUrl ? <p className="mt-3 break-all text-xs text-sage-deep">{copy.copied}: <a href={shareUrl} target="_blank" rel="noreferrer" className="underline">{shareUrl}</a></p> : null}</section>
    <div className="mt-6 flex flex-wrap items-center justify-between gap-3 px-1"><p className="text-sm text-ink-soft" role="status">{saveState === "saving" ? copy.saving : saveState === "saved" ? copy.saved : memoir.status === "completed" ? copy.completedStatus : copy.draftStatus}</p><button type="button" disabled={busy || saveState === "saving"} onClick={() => void finishEditing()} className="rounded-full bg-sage-deep px-5 py-2.5 text-sm text-paper disabled:opacity-50">{copy.complete}</button></div>
  </div></main>;
}
