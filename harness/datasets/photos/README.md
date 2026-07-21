# photos/ —— 拍照识别评测图片

本目录存放 `photo` 类评测的固定图片。正样本采用 Wikimedia Commons 上有明确许可的澳门地标照片；
评测只使用缩放后的副本，文件页与许可如下。

| 本地文件 | 目标 POI | 来源 / 作者 | 许可 |
|---|---|---|---|
| `senado_square.jpg` | 议事亭前地 | [Largo do Senado.jpg](https://commons.wikimedia.org/wiki/File:Largo_do_Senado.jpg)，Iolaire / Netsonfong | CC BY-SA 2.0 |
| `ama_temple.jpg` | 妈祖阁（妈阁庙） | [A-Ma Temple, Macau, built 1488 (23)](https://commons.wikimedia.org/wiki/File:A-Ma_Temple,_Macau,_built_1488_(23)_(32815782406).jpg)，Richard Mortel | CC BY 2.0 |
| `st_pauls.jpg` | 大三巴牌坊 | [Ruins of Saint Paul in Macau.jpg](https://commons.wikimedia.org/wiki/File:Ruins_of_Saint_Paul_in_Macau.jpg)，Kent Wong | CC0 1.0 |
| `taipa_houses.jpg` | 龙环葡韵 | [Taipa Houses–Museum 1.jpg](https://commons.wikimedia.org/wiki/File:Taipa_Houses%E2%80%93Museum_1.jpg)，SH6188 / Streetdeck | CC BY-SA 4.0 |
| `senado_tiles.jpg` | 议事亭前地（碎石路局部） | [Senate Square Tiles in Macau.jpg](https://commons.wikimedia.org/wiki/File:Senate_Square_Tiles_in_Macau.jpg)，The Red Hat of Pat Ferrick | Public Domain |
| `ama_temple_entrance.jpg` | 妈祖阁（入口全景） | [A-Ma Temple, 2023 (01).jpg](https://commons.wikimedia.org/wiki/File:A-Ma_Temple,_2023_(01).jpg)，Bahnfrend | CC BY-SA 4.0 |
| `st_pauls_steps.jpg` | 大三巴牌坊（石阶远景） | [The Ruins of St. Paul's in Macau.jpg](https://commons.wikimedia.org/wiki/File:The_Ruins_of_St._Paul%27s_in_Macau.jpg)，BenjPhoto | CC BY-SA 4.0 |
| `taipa_houses_wide.jpg` | 龙环葡韵（建筑群） | [Taipa Houses Museum 01.JPG](https://commons.wikimedia.org/wiki/File:Taipa_Houses_Museum_01.JPG)，Abasaa | Public Domain |
| `st_dominic_front.jpg` | 玫瑰堂（横景） | [St. Dominic's Church, Macau.jpg](https://commons.wikimedia.org/wiki/File:St._Dominic%27s_Church,_Macau.jpg)，Jenchanted | CC BY-SA 3.0 |
| `st_dominic_tall.jpg` | 玫瑰堂（竖景） | [St Dominic's Church.jpg](https://commons.wikimedia.org/wiki/File:St_Dominic%27s_Church.jpg)，Anthony Hartman | CC BY 2.0 |
| `guia_lighthouse_front.jpg` | 东望洋灯塔（近景） | [Guia Lighthouse 22-02-2023 (2).jpg](https://commons.wikimedia.org/wiki/File:Capela_de_Nossa_Senhora_da_Guia_and_Macau_Guia_Lighthouse_22-02-2023%282%29.jpg)，LN9267 | CC BY-SA 4.0 |
| `guia_lighthouse_side.jpg` | 东望洋灯塔（全景） | [Guia Lighthouse 22-02-2023 (3).jpg](https://commons.wikimedia.org/wiki/File:Capela_de_Nossa_Senhora_da_Guia_and_Macau_Guia_Lighthouse_22-02-2023%283%29.jpg)，LN9267 | CC BY-SA 4.0 |
| `negative_eiffel.jpg` | 非澳门负样本（埃菲尔铁塔） | [The Eiffel Tower in Paris.jpg](https://commons.wikimedia.org/wiki/File:The_Eiffel_Tower_in_Paris.jpg)，Jeong seolah | CC0 1.0 |
| `negative_sydney.jpg` | 非澳门负样本（悉尼歌剧院） | [Sydney Opera House (2017).jpg](https://commons.wikimedia.org/wiki/File:Sydney_Opera_House_%282017%29.jpg)，Pxhere / 未知作者 | CC0 1.0 |

其余负样本复用仓库已有的非景点图片，不在本目录复制：

- `assets/style_reference_gantt.jpg`：项目甘特图，期望不猜 POI。
- `background/keyword_frequency.png`：调研关键词图，期望不猜 POI。
- `background/expression_types.png`：调研表达类型图，期望不猜 POI。
- `background/confusion_expression_breakdown.png`：困惑表达图，期望不猜 POI。
- `background/physical_burden_breakdown.png`：体力负担图，期望不猜 POI。
- `background/sample_overview.png`：样本概览图，期望不猜 POI。

评测共 20 条：12 条 POI 正样本（6 个景点、每个两个视角）和 8 条负样本（2 条外地地标、6 条非实景图表）。
运行器会把图片复制为随机临时文件名再交给 Agent，避免从文件名泄露答案。

> 图片只用于开发期自动评测；新增或替换图片时必须同时更新来源、许可与 `cases.json`。

## 明信片参考图（phase 1）

批量从网上收集的 POI 实景参考图放在子目录 **[`poi_refs/`](./poi_refs/)**（按 `poi_id` 命名），
与上方评测固定集分开，避免混用。收集命令见该目录 README。
