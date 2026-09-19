from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
SHOT_DIR = ROOT / "screenshots"
OUTPUT = ROOT / "StoryWalk_用户使用动线与错误提示演示指南_可编辑版.docx"

# Named portability override for editable text.  Hiragino Sans GB ships with
# macOS, contains the complete Simplified Chinese glyph set, and is also
# recognized by Word's East Asian font slots.
FONT_NAME = "Arial Unicode MS"

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
INK = "20252B"
MUTED = "5F6B76"
PALE_BLUE = "E8EEF5"
PALE_GRAY = "F2F4F7"
PALE_RED = "FBEAEC"
RED = "9B1C1C"
WHITE = "FFFFFF"
LINE = "CCD5DF"


SCREENS = [
    {
        "file": "01-language-home.png",
        "group": "开始旅程",
        "title": "语言选择首页",
        "purpose": "让用户在进入产品前选择界面语言，并理解 StoryWalk 的定位与隐私说明。",
        "action": "选择简体中文、繁体中文、English 或 Português；随后选择“Begin the walk”或“Log in / Sign up”。",
        "next": "游客可直接进入偏好设置；需要保存行程与回忆的用户进入登录/注册。",
    },
    {
        "file": "02-login.png",
        "group": "账号入口",
        "title": "登录页面",
        "purpose": "使用邮箱或手机号登录，并提供忘记密码及返回首页入口。",
        "action": "填写邮箱或手机号与密码，点击“登录”。",
        "next": "登录成功后返回用户原本想访问的页面；未注册用户切换到注册页。",
    },
    {
        "file": "03-login-error-required.png",
        "group": "账号入口",
        "title": "登录必填项错误",
        "purpose": "阻止空表单提交，并在字段附近给出明确修正提示。",
        "action": "未填写邮箱/手机号与密码时点击“登录”。",
        "next": "补充至少一种账号标识并输入密码后重新提交。",
        "error": "触发“邮箱和手机至少填一个”“请输入密码”。",
    },
    {
        "file": "04-register-top.png",
        "group": "账号入口",
        "title": "注册页面（上半页）",
        "purpose": "创建新账号，收集邮箱/手机号、密码与昵称。",
        "action": "至少填写邮箱或手机号，并设置不少于 6 个字符的密码。",
        "next": "继续向下设置安全问题、地区与确认语言。",
    },
    {
        "file": "04b-register-security.png",
        "group": "账号入口",
        "title": "注册页面（安全问题）",
        "purpose": "在注册时配置忘记密码所需的身份验证证据。",
        "action": "选择一个安全问题并填写答案；答案在数据库中以哈希形式保存。",
        "next": "提交注册后进入产品；已有邮箱会被阻止并引导直接登录。",
    },
    {
        "file": "07-preferences-ai.png",
        "group": "规划路线",
        "title": "AI 偏好对话",
        "purpose": "通过逐问逐答收集旅行时长、同行人、兴趣和步行偏好。",
        "action": "在输入框回答引导问题；也可点击 Skip 直接使用手动设置。",
        "next": "系统将答案映射为结构化偏好，供用户确认和微调。",
    },
    {
        "file": "08-preferences-weather.png",
        "group": "规划路线",
        "title": "到达日期、天气与交通提示",
        "purpose": "根据到达日期展示澳门天气、出行建议、公交与开放时间来源。",
        "action": "选择到达日期并阅读实时信息；天气请求失败时可重试，偏好表仍可继续填写。",
        "next": "向下确认时长与故事体验。",
    },
    {
        "file": "09-preferences-duration-story.png",
        "group": "规划路线",
        "title": "时长与故事体验",
        "purpose": "确定半日、全日、夜游或多日行程，并可选一个主题故事。",
        "action": "选择时长；故事体验可跳过，不影响普通路线生成。",
        "next": "继续选择口岸、主题、兴趣和步行限制。",
    },
    {
        "file": "10-preferences-themes.png",
        "group": "规划路线",
        "title": "口岸、主题与兴趣",
        "purpose": "将用户的入境/离境条件与内容兴趣转换为路线约束。",
        "action": "口岸为可选项；主题和兴趣支持多选。",
        "next": "继续选择同行人与步行风格。",
    },
    {
        "file": "11-preferences-walking.png",
        "group": "规划路线",
        "title": "步行风格与补充要求",
        "purpose": "收集少走路、少爬坡、遮阴、室内优先和无障碍等实际需求。",
        "action": "多选步行偏好，并可输入自由文本补充要求；点击生成路线。",
        "next": "进入路线结果页。",
    },
    {
        "file": "05-route-result-top.png",
        "group": "执行行程",
        "title": "路线结果（总览）",
        "purpose": "展示地图、路线主题、总停靠点、距离、时长及匹配理由。",
        "action": "查看地图与路线摘要；可用自然语言要求 AI 调整路线。",
        "next": "开始行程或向下逐站浏览。",
    },
    {
        "file": "06-route-result-stops.png",
        "group": "执行行程",
        "title": "路线结果（站点与进度）",
        "purpose": "按顺序展示各站点、预计停留时间、步行/公交提示与到站操作。",
        "action": "到达后完成站点记录；可使用 GPS 验证或演示用模拟到站。",
        "next": "从站点进入景点导览、故事体验或完成后的纪念内容。",
    },
    {
        "file": "12-guide-search.png",
        "group": "景点导览",
        "title": "景点搜索",
        "purpose": "让用户随时查询澳门景点，而不必依赖当前路线。",
        "action": "搜索或从列表选择景点，也可通过照片识别入口查找。",
        "next": "打开景点详情与现场讲解。",
    },
    {
        "file": "13-guide-detail-top.png",
        "group": "景点导览",
        "title": "景点详情与场景图",
        "purpose": "展示景点图片、分类及现场讲解入口。",
        "action": "阅读场景简介，或上传/拍摄照片进行景点识别。",
        "next": "向下阅读分段讲解并播放本地语音。",
    },
    {
        "file": "14-guide-narration.png",
        "group": "景点导览",
        "title": "分段讲解与本地语音",
        "purpose": "以“为什么重要、历史故事、观察要点、本地故事”等模块组织内容。",
        "action": "阅读讲解或点击播放；语音在设备本地生成，不上传录音。",
        "next": "继续查看建议问题或自行追问。",
    },
    {
        "file": "15-guide-followup.png",
        "group": "景点导览",
        "title": "AI 追问",
        "purpose": "围绕当前景点继续探索历史变化、现场细节和最佳观赏位置。",
        "action": "点击建议问题，或输入自定义问题后发送。",
        "next": "返回景点列表或回到行程。",
    },
    {
        "file": "16-story-selection.png",
        "group": "故事体验",
        "title": "故事选择",
        "purpose": "展示三条独立 StoryWalk 旅程及区域、主题和预计时长。",
        "action": "选择澳门半岛、氹仔或路环故事。",
        "next": "进入故事封面了解背景和安全要求。",
    },
    {
        "file": "17-story-cover.png",
        "group": "故事体验",
        "title": "故事封面与安全说明",
        "purpose": "在开始前解释叙事背景、真实地点数量、谜题数量与安全规则。",
        "action": "阅读提示后开始故事；所有谜题均可跳过。",
        "next": "进入章节地图。",
    },
    {
        "file": "18-story-map.png",
        "group": "故事体验",
        "title": "章节地图与任务进度",
        "purpose": "显示当前任务、已收集物、章节时间线与锁定状态。",
        "action": "打开已解锁章节，或进入当前章节继续。",
        "next": "进入现场到达确认与章节互动。",
    },
    {
        "file": "19-story-scene-arrival.png",
        "group": "故事体验",
        "title": "章节到达确认",
        "purpose": "先要求用户确认处于公开安全区域，再继续故事。",
        "action": "确认周围安全后点击“I have arrived”；无需依赖 GPS。",
        "next": "进入本章节叙事与谜题。",
    },
    {
        "file": "20-profile-security.png",
        "group": "个人中心",
        "title": "账号与安全设置",
        "purpose": "集中展示登录账号、修改密码与安全问题配置。",
        "action": "修改密码时需验证当前密码；修改安全问题同样需要当前密码。",
        "next": "继续管理偏好，或从侧栏进入回忆录与明信片。",
    },
    {
        "file": "21-password-error-required.png",
        "group": "个人中心",
        "title": "密码修改必填错误",
        "purpose": "利用浏览器原生校验阻止空字段或过短密码提交。",
        "action": "直接点击“Save new password”而未填写必填字段。",
        "next": "填写当前密码、新密码和确认密码；两次新密码必须一致。",
        "error": "空字段触发必填提示；当前密码错误或两次新密码不一致会显示页面错误。",
    },
    {
        "file": "22-profile-preferences.png",
        "group": "个人中心",
        "title": "个人偏好维护",
        "purpose": "让用户随时修改语言、时长、故事选择、兴趣及步行风格。",
        "action": "更新后保存偏好；如需立即应用，可重新生成行程。",
        "next": "返回行程或进入个人内容。",
    },
    {
        "file": "23-forgot-password.png",
        "group": "账号找回",
        "title": "忘记密码入口",
        "purpose": "先通过注册邮箱查找安全问题，再允许设置新密码。",
        "action": "输入注册邮箱并点击“下一步”。",
        "next": "回答注册时设置的安全问题，并输入两次新密码。",
    },
    {
        "file": "24-forgot-error-required.png",
        "group": "账号找回",
        "title": "忘记密码必填错误",
        "purpose": "阻止未填写注册邮箱时继续。",
        "action": "邮箱为空时点击“下一步”。",
        "next": "填写完整邮箱地址后重试。",
        "error": "触发浏览器原生邮箱必填/格式校验。",
    },
    {
        "file": "25-memoir-gallery-top.png",
        "group": "旅行回忆",
        "title": "回忆录总览与统计",
        "purpose": "优先展示照片数和回忆录数，再列出各次旅行回忆录。",
        "action": "点击任一回忆录打开编辑器。",
        "next": "向下查看照片墙与历史行程。",
    },
    {
        "file": "26-memoir-gallery-photo-history.png",
        "group": "旅行回忆",
        "title": "照片墙与旅行历史",
        "purpose": "按照片与行程重访旅程，并从已完成行程创建或打开回忆录。",
        "action": "打开照片关联的回忆录，或从历史行程创建回忆录。",
        "next": "进入回忆录编辑。",
    },
    {
        "file": "27-memoir-editor-top.png",
        "group": "旅行回忆",
        "title": "回忆录编辑（标题与章节）",
        "purpose": "编辑标题、序言和按实际到访顺序生成的旅行章节。",
        "action": "决定章节是否收入回忆录，并补充章节叙述或个人备注。",
        "next": "向下管理真实照片。",
    },
    {
        "file": "28-memoir-editor-photo.png",
        "group": "旅行回忆",
        "title": "回忆录真实照片",
        "purpose": "上传并关联真实照片，标记人物照片并选择封面。",
        "action": "选择关联地点和人物标记后上传；可设为封面。",
        "next": "配置分享隐私。",
    },
    {
        "file": "29-memoir-editor-sharing.png",
        "group": "旅行回忆",
        "title": "回忆录分享与隐私",
        "purpose": "默认保持私密；只有主动生成链接后才提供隐私裁剪版本。",
        "action": "选择隐藏人物、日期、精确路线或个人备注，再生成分享链接。",
        "next": "完成编辑或撤销已有分享链接。",
    },
    {
        "file": "30-postcards-gallery-top.png",
        "group": "旅行纪念",
        "title": "明信片画廊（上半页）",
        "purpose": "按到访顺序汇总已生成的旅行明信片与记忆摘要。",
        "action": "浏览画廊或分享记忆相册。",
        "next": "向下查看具体卡片并选择一张。",
    },
    {
        "file": "31-postcards-gallery-list.png",
        "group": "旅行纪念",
        "title": "明信片画廊（卡片列表）",
        "purpose": "展示场景图、地点、时间与路线信息，并标记 AI 场景。",
        "action": "点击卡片查看详情；已到访但未制作的地点可创建明信片。",
        "next": "进入明信片详情。",
    },
    {
        "file": "32-postcard-detail.png",
        "group": "旅行纪念",
        "title": "明信片详情",
        "purpose": "展示完整明信片、时间、地点、路线及下载/分享入口。",
        "action": "可下载、分享或重新生成；删除会移除该明信片。",
        "next": "返回画廊继续浏览。",
        "error": "生成失败时显示“场景图片暂未生成成功…请重试”；下载失败会提示稍后重试。",
    },
    {
        "file": "33-login-error-account-not-found.png",
        "group": "错误状态示例",
        "title": "账户不存在或凭据无效",
        "purpose": "使用统一、不过度泄露账号状态的登录错误提示。",
        "action": "使用虚构测试邮箱和密码提交登录。",
        "next": "检查邮箱/手机号，改用正确账号，或前往注册/忘记密码。",
        "error": "触发“没有找到这个账户”。截图使用虚构数据，未影响演示账号。",
    },
    {
        "file": "34-register-error-password-mismatch.png",
        "group": "错误状态示例",
        "title": "注册密码不一致",
        "purpose": "在请求发出前阻止两次密码不一致的注册。",
        "action": "使用虚构测试资料，并输入两组不同密码。",
        "next": "使确认密码与密码完全一致后重新注册。",
        "error": "触发“两次输入的密码不一致”。截图未创建账号。",
    },
]


ERROR_ROWS = [
    ("登录", "未填写邮箱和手机号", "邮箱和手机至少填一个", "补充邮箱或完整手机号"),
    ("登录", "密码为空", "请输入密码", "输入密码后重新提交"),
    ("登录", "账号不存在或登录凭据无效", "没有找到这个账户", "核对账号；也可注册或找回密码"),
    ("注册", "邮箱格式不完整", "请输入完整的邮箱地址，例如 name@example.com", "修正邮箱格式"),
    ("注册", "密码少于 6 个字符", "密码至少需要 6 个字符", "使用至少 6 个字符"),
    ("注册", "两次密码不同", "两次输入的密码不一致", "重新填写确认密码"),
    ("注册", "数据库已有相同邮箱", "邮箱已经存在，请更换邮箱或直接登录", "更换邮箱或点击直接登录"),
    ("修改密码", "当前密码错误", "当前密码不正确", "输入正确当前密码"),
    ("修改密码", "两次新密码不同", "两次输入的新密码不一致", "重新填写确认密码"),
    ("找回密码", "邮箱未配置安全问题或不存在", "该邮箱没有配置安全问题，无法通过此方式找回", "使用已配置账号或联系维护者"),
    ("找回密码", "安全问题答案错误", "安全问题答案不正确", "检查答案后重试"),
    ("找回密码", "两次新密码不同", "两次输入的密码不一致", "重新填写确认密码"),
    ("天气", "天气/实时信息接口暂时不可用", "天气提醒暂时不可用", "点击重试；仍可继续填写偏好"),
    ("导览", "景点或图片内容加载失败", "页面错误状态 + 重试按钮", "检查网络/后端后重试"),
    ("明信片", "场景图生成或下载失败", "场景图片暂未生成成功 / 下载失败，请稍后重试", "保留行程数据，稍后重新生成或下载"),
]


def set_run_font(run, size: float | None = None, bold: bool | None = None,
                 color: str | None = None, italic: bool | None = None) -> None:
    run.font.name = FONT_NAME
    fonts = run._element.get_or_add_rPr().rFonts
    for slot in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(slot), FONT_NAME)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def configure_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = FONT_NAME
    for slot in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        normal._element.rPr.rFonts.set(qn(slot), FONT_NAME)
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    specs = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, DARK_BLUE, 10, 5),
    }
    for name, (size, color, before, after) in specs.items():
        style = doc.styles[name]
        style.font.name = FONT_NAME
        for slot in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            style._element.rPr.rFonts.set(qn(slot), FONT_NAME)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for list_name in ("List Bullet", "List Number"):
        style = doc.styles[list_name]
        style.font.name = FONT_NAME
        for slot in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            style._element.rPr.rFonts.set(qn(slot), FONT_NAME)
        style.font.size = Pt(11)
        style.paragraph_format.left_indent = Inches(0.375)
        style.paragraph_format.first_line_indent = Inches(-0.188)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25


def shade_paragraph(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = p_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        p_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])
    set_run_font(run, size=9, color=MUTED)


def set_page_furniture(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.72)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    section.different_first_page_header_footer = True

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    hp.paragraph_format.space_after = Pt(0)
    hr = hp.add_run("STORYWALK · 产品操作指南")
    set_run_font(hr, size=9, bold=True, color=MUTED)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    fr = fp.add_run("StoryWalk  |  ")
    set_run_font(fr, size=9, color=MUTED)
    add_field(fp, "PAGE")


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths: list[int], indent: int = 120) -> None:
    total = sum(widths)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")
    tbl_w = tbl_pr.find(qn("w:tblW"))
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent))
    tbl_ind.set(qn("w:type"), "dxa")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            width = widths[idx]
            cell.width = Inches(width / 1440)
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def repeat_header_row(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def add_cover(doc: Document) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(22)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run("产品演示手册")
    set_run_font(r, size=10.5, bold=True, color=BLUE)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run("StoryWalk 用户使用动线")
    set_run_font(r, size=29, bold=True, color=INK)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(18)
    r = p.add_run("逐页截图、操作说明与错误提示触发指南")
    set_run_font(r, size=15, color=DARK_BLUE)

    pic_p = doc.add_paragraph()
    pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_p.paragraph_format.space_after = Pt(12)
    inline = pic_p.add_run().add_picture(str(SHOT_DIR / "01-language-home.png"), width=Inches(6.2))
    inline._inline.docPr.set("descr", "StoryWalk 语言选择首页")

    meta = doc.add_paragraph()
    meta.paragraph_format.space_before = Pt(6)
    meta.paragraph_format.space_after = Pt(5)
    meta.add_run("用途：").bold = True
    meta.add_run("项目演示、用户验收、答辩讲解与测试复现")
    for run in meta.runs:
        set_run_font(run, size=10.5, color=INK)

    meta = doc.add_paragraph()
    meta.paragraph_format.space_after = Pt(5)
    meta.add_run("截图环境：").bold = True
    meta.add_run("Google Chrome · 本地开发环境 · 2026-08-31")
    for run in meta.runs:
        set_run_font(run, size=10.5, color=INK)

    note = doc.add_paragraph()
    note.paragraph_format.space_before = Pt(12)
    note.paragraph_format.space_after = Pt(0)
    shade_paragraph(note, PALE_BLUE)
    nr = note.add_run("隐私说明  ")
    set_run_font(nr, size=10, bold=True, color=DARK_BLUE)
    nr = note.add_run("文档不包含真实密码或安全问题答案；错误截图使用虚构测试数据。")
    set_run_font(nr, size=10, color=INK)


def add_overview(doc: Document) -> None:
    doc.add_page_break()
    doc.add_heading("用户主线总览", level=1)
    intro = doc.add_paragraph(
        "本指南按一次完整旅行体验组织。演示时可沿下列顺序讲解；每个页面后的“下一步”可直接作为口播衔接。"
    )
    intro.paragraph_format.space_after = Pt(10)

    flow = [
        "选择语言，决定以游客方式开始或登录账号。",
        "登录/注册，并在注册时设置安全问题。",
        "通过 AI 对话或手动选项确认旅行偏好与到达日期。",
        "生成路线，按站点推进并使用景点导览或 StoryWalk。",
        "在个人中心维护密码、安全问题与长期偏好。",
        "用回忆录整理真实照片、章节和分享隐私。",
        "用明信片保存每个到访地点，并处理下载、分享或重新生成。",
    ]
    for item in flow:
        p = doc.add_paragraph(item, style="List Number")
        p.paragraph_format.keep_with_next = False

    doc.add_heading("截图阅读方式", level=2)
    p = doc.add_paragraph()
    p.add_run("页面目的：").bold = True
    p.add_run("为什么用户会来到此页。")
    p = doc.add_paragraph()
    p.add_run("用户动作：").bold = True
    p.add_run("演示时应执行或说明的核心操作。")
    p = doc.add_paragraph()
    p.add_run("下一步：").bold = True
    p.add_run("完成当前动作后的自然去向。")
    p = doc.add_paragraph()
    p.add_run("错误触发：").bold = True
    p.add_run("出现提示的条件及建议恢复方式；没有必要实际修改演示账号。")
    for para in doc.paragraphs[-4:]:
        for run in para.runs:
            set_run_font(run, size=10.5, color=INK)


def add_screenshot_page(doc: Document, index: int, item: dict[str, str]) -> None:
    doc.add_page_break()
    kicker = doc.add_paragraph()
    kicker.paragraph_format.space_after = Pt(2)
    kr = kicker.add_run(f"{item['group']}  ·  STEP {index:02d}")
    set_run_font(kr, size=9.5, bold=True, color=BLUE)

    title = doc.add_heading(item["title"], level=1)
    title.paragraph_format.space_before = Pt(0)

    image_path = SHOT_DIR / item["file"]
    pic_p = doc.add_paragraph()
    pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_p.paragraph_format.space_before = Pt(2)
    pic_p.paragraph_format.space_after = Pt(4)
    pic_p.paragraph_format.keep_with_next = True
    inline = pic_p.add_run().add_picture(str(image_path), width=Inches(6.25))
    inline._inline.docPr.set("descr", f"{item['title']} 页面截图")

    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    cap.paragraph_format.keep_with_next = True
    cr = cap.add_run(f"图 {index}  {item['title']}（Chrome 实际页面）")
    set_run_font(cr, size=8.5, italic=True, color=MUTED)

    for label, key in (("页面目的", "purpose"), ("用户动作", "action"), ("下一步", "next")):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        lr = p.add_run(f"{label}  ")
        set_run_font(lr, size=10.2, bold=True, color=DARK_BLUE)
        vr = p.add_run(item[key])
        set_run_font(vr, size=10.2, color=INK)

    if item.get("error"):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(0)
        shade_paragraph(p, PALE_RED)
        lr = p.add_run("错误触发  ")
        set_run_font(lr, size=10, bold=True, color=RED)
        vr = p.add_run(item["error"])
        set_run_font(vr, size=10, color=INK)


def add_error_matrix(doc: Document) -> None:
    doc.add_page_break()
    doc.add_heading("错误提示触发表", level=1)
    p = doc.add_paragraph(
        "以下提示用于演示和验收。优先在虚构测试资料或空表单上复现；不要为了截图反复尝试真实账号密码或安全答案。"
    )
    p.paragraph_format.space_after = Pt(10)

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    widths = [1080, 2160, 3420, 2700]
    headers = ["区域", "触发条件", "用户看到的提示", "建议恢复"]
    for idx, text in enumerate(headers):
        cell = table.rows[0].cells[idx]
        set_cell_shading(cell, PALE_BLUE)
        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_after = Pt(0)
        run = cp.add_run(text)
        set_run_font(run, size=9, bold=True, color=DARK_BLUE)
    repeat_header_row(table.rows[0])

    for row_index, row_data in enumerate(ERROR_ROWS):
        cells = table.add_row().cells
        if row_index % 2:
            for cell in cells:
                set_cell_shading(cell, PALE_GRAY)
        for col_index, text in enumerate(row_data):
            cp = cells[col_index].paragraphs[0]
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_index == 0 else WD_ALIGN_PARAGRAPH.LEFT
            cp.paragraph_format.space_before = Pt(0)
            cp.paragraph_format.space_after = Pt(0)
            cp.paragraph_format.line_spacing = 1.15
            run = cp.add_run(text)
            set_run_font(run, size=8.4, bold=(col_index == 0), color=INK)

    set_table_geometry(table, widths)

    doc.add_heading("演示注意事项", level=2)
    notes = [
        "注册重复邮箱：使用已存在账号时会明确提示更换邮箱或直接登录；不要在演示中创建重复数据。",
        "修改密码：可以展示表单与校验，但最终提交会改变账号密码，演示前应确认。",
        "安全问题：答案不会明文展示；找回密码时仅显示问题文本。",
        "天气/地图/图片失败：保留用户当前选择，提供重试或降级说明，不应清空行程。",
        "删除明信片、撤销分享链接等不可逆或影响分享状态的操作，不建议在主演示账号上执行。",
    ]
    for note in notes:
        doc.add_paragraph(note, style="List Bullet")


def build() -> Path:
    doc = Document()
    configure_styles(doc)
    set_page_furniture(doc)
    props = doc.core_properties
    props.title = "StoryWalk 用户使用动线与错误提示演示指南"
    props.subject = "StoryWalk 产品逐页操作截图与错误触发说明"
    props.author = "StoryWalk Project Team"
    props.keywords = "StoryWalk, 用户动线, 演示, 错误提示, Word"

    add_cover(doc)
    add_overview(doc)
    for idx, item in enumerate(SCREENS, start=1):
        add_screenshot_page(doc, idx, item)
    add_error_matrix(doc)

    doc.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(path)
