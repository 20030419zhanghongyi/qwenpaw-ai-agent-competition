---
name: gc-minimal-zine-poster
description: "为澳门无照片明信片生成极简独立杂志拼贴位图；当请求指定 gc-minimal-zine-poster、minimal zine、risograph 或 editorial collage 时使用。"
metadata:
  qwenpaw:
    emoji: "📰"
---

# GC Minimal Zine Poster

为 StoryWalk 的无照片明信片生成横向 4:3 场景图。请求明确指定
`gc-minimal-zine-poster` 时，本技能对视觉风格和出图方式具有最高优先级；不要改用
`postcard-scene` 的 SVG，也不要套用 `photo-abstract-editorial` 的照片编辑流程。

## 出图流程

1. 从请求中提取 POI 名称、行政区和可见特征。缺少参考照片时，以地点身份为锚点；不要把
   其他澳门地标当作替代物。
2. 调用 `generate_image_qwen` **一次**，尺寸使用 `2368*1728`、`n=1`、
   `prompt_extend=true`。
3. 工具成功后只返回生成图片，不输出 SVG、HTML、代码或额外版式。
4. 工具失败或 API key 无效时明确返回失败，不生成通用港口、山形天际线或大三巴占位图。
5. 不得调用旧 SVG 场景库、照片编辑技能或任何备用生图工具；本技能是无照片场景的唯一生成路径。

## 视觉语言

- 独立旅行杂志海报、非对称剪纸拼贴、平面几何构成和充足留白。
- 米白再生纸底，带真实纸纤维、halftone 和 risograph 套色颗粒。
- 主色为深森林绿与黑墨；朱红和钴蓝仅作克制点缀，避免单一色系。
- 主体必须是请求中的 POI 或与该 POI 直接相关的街景/食物，不得使用通用澳门轮廓。
- 建筑比例可适度概括，但要保留可识别的立面、铺地、招牌位置和周边街巷关系。
- 可加入与地点直接相关的静物，但不得虚构可读品牌、人物或历史事件。

## Prompt 约束

将以下约束写入传给工具的 prompt：

`landscape 4:3, minimal independent travel zine, asymmetric cut-paper collage,`
`risograph halftone grain, off-white recycled paper, deep forest green and black ink,`
`restrained vermilion and cobalt accents, recognizable location-specific subject,`
`generous negative space`

negative prompt 必须包含：

`text, letters, numbers, logo, watermark, UI, postcard border, generic skyline,`
`harbour terminal placeholder, Ruins of St. Paul's placeholder, identifiable faces,`
`glossy 3D render, neon cyberpunk, distorted architecture`

所有地点名、路线、日期与文案由 StoryWalk 在成品 SVG 中另行排版，图片内部不得生成文字。
