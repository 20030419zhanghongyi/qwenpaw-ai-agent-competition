# POI 与路线数据来源

> 最后核验日期：2026-07-07
> URL 不写入 JSON；本文件用于人工复核。坐标采用 WGS84，地图对象来自 OpenStreetMap；路线距离来自其专用步行路由服务。

## POI

### poi_senado — 议事亭前地
- 变更：修改（坐标、district、theme、intro、history、architecture、story、observation_tips、suitable_for）
- 来源类型：official
- 来源：
  - [议事亭前地](https://www.wh.mo/gb/site/detail/12)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：说明名称来源、长期城市中心功能、喷水池、两侧建筑年代及1993年起的波浪碎石铺地。
  - [OpenStreetMap 对象 way/192573684](https://www.openstreetmap.org/way/192573684)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：原坐标偏离实际广场，已按地图对象中心点修正；未写入客流和最佳拍摄时间。

### poi_paixao — 恋爱巷
- 变更：修改（坐标、district、theme、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [恋爱巷](https://www.macaotourism.gov.mo/zh-hans/macao-full-of-fun/world-heritage-tour-in-central-district/travessa-da-paixao)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, name_pt, intro, history, story
    - 证据摘要：解释葡文街名、中文译名的文化联想，以及影视取景和电影馆的联系。
  - [OpenStreetMap 对象 way/306982652](https://www.openstreetmap.org/way/306982652)
    - 支持字段：coordinates, district
- 冲突或局限：删除“约50米”、特定视线和顺光时段等未被具体来源充分支持的说法。

### poi_fatong — 疯堂斜巷
- 变更：修改（坐标、theme、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [艺竹苑（仁慈堂婆仔屋）](https://www.macaotourism.gov.mo/zh-hans/step-out-macao/st-lazarus-parish/albergue-scm)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：intro, architecture, story, district
    - 证据摘要：确认疯堂斜巷8号的艺竹苑、黄色葡式建筑及望德堂文艺游语境。
  - [OpenStreetMap 对象 way/402359733](https://www.openstreetmap.org/way/402359733)
    - 支持字段：coordinates, name_pt, district
- 冲突或局限：未找到足以支持街巷开辟年代的官方资料，因此删除原有麻风院年代和街巷史推断。

### poi_sv_lazaro — 望德圣母堂
- 变更：修改（由街区级“望德堂区”改为真实教堂节点；坐标、名称及全部说明文本）
- 来源类型：official
- 来源：
  - [望德圣母堂](https://www.macaotourism.gov.mo/zh-hant/sightseeing/churches/st-lazarus-church)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：记载首座主教座堂、1576年教区背景、1885年重建、1957年修葺及麻风院相关称谓。
  - [OpenStreetMap 对象 node/4416596892](https://www.openstreetmap.org/node/4416596892)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：保留既有稳定 ID 以避免悬空引用，但名称改为具体 POI。

### poi_florindo — 福隆新街
- 变更：修改（坐标、district、theme、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [中珠澳玩乐指南（第52–53页）](https://content.macaotourism.gov.mo/uploads/mgto_brochures/68fdeff1fdcf6aca24a5b36a8084a13f0e504b3f.pdf)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：intro, history, story
    - 证据摘要：将福隆新街列为澳门新八景之一，说明其为著名老街，往日娱乐业集中、现为美食手信区域。
  - [OpenStreetMap 对象 way/306854022](https://www.openstreetmap.org/way/306854022)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：删除清同治填海、统一“虾酱红”材料和黄昏灯笼等未完成官方交叉核验的细节。

### poi_xiahuan — 下环街市
- 变更：修改（坐标、theme、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [市政署公共街市摊位文件](https://www.iam.gov.mo/Content/List21/56a70022-5218-494c-ad32-a954d818f1c2/%E7%AB%A0%E7%A8%8B-%E4%B8%AD%E6%96%87.pdf)
    - 发布机构：澳门特别行政区政府市政署
    - 访问日期：2026-07-06
    - 支持字段：name_zh, name_en, name_pt, intro, history, story
    - 证据摘要：官方文件确认下环街市属于市政署公共街市及其葡英文名称，并涉及摊位经营。
  - [OpenStreetMap 对象 node/2165427401](https://www.openstreetmap.org/node/2165427401)
    - 支持字段：coordinates, district
- 冲突或局限：未找到可靠官方沿革和建筑风格资料，相关字段明确保守处理；不承诺熟食档或营业状态。

### poi_ama — 妈祖阁（妈阁庙）
- 变更：修改（坐标、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [妈祖阁（妈阁庙）](https://www.wh.mo/gb/site/detail/1)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：说明创建年份未定、神山第一殿的1605年实物证据、建筑组成、依山布局及摩崖石刻价值。
  - [OpenStreetMap 对象 way/192187333](https://www.openstreetmap.org/way/192187333)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：删除“15世纪末始建”和地名来源等较强断言，采用文化局更审慎的年代表述。

### poi_lilau — 亚婆井前地
- 变更：修改（坐标、district、全部说明文本、source_type）
- 来源类型：folklore
- 来源：
  - [亚婆井前地](https://www.wh.mo/gb/site/detail/3)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：intro, history, architecture, story
    - 证据摘要：说明Lilau意为山泉、早期水源和聚居历史、周边葡式住宅与装饰艺术公寓，并记录葡人民谣。
  - [OpenStreetMap 对象 way/231345560](https://www.openstreetmap.org/way/231345560)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：民谣以“相传”表述并将 source_type 标为 folklore，不当作历史事件。

### poi_rua_cunha — 官也街
- 变更：修改（坐标、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [官也街](https://www.macaotourism.gov.mo/zh-hans/macao-full-of-fun/portuguese-ambiance-tour-at-taipa-island/rua-do-cunha)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：intro, history, story
    - 证据摘要：确认1983年成为澳门首个行人专用区、餐饮零售功能，以及旧街市迁出后于2003年改为广场。
  - [OpenStreetMap 对象 way/183607324](https://www.openstreetmap.org/way/183607324)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：删除“19世纪街名来源”和实时热门程度，营业与排队不作固定判断。

### poi_carmo — 嘉模圣母堂
- 变更：修改（坐标、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [嘉模圣母堂](https://www.macaotourism.gov.mo/zh-hans/sightseeing/churches/our-lady-of-carmel-church)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, story
    - 证据摘要：确认教堂位置、1885年建造、1985年重修及氹仔唯一天主教堂的描述。
  - [OpenStreetMap 对象 way/331666100](https://www.openstreetmap.org/way/331666100)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：不再将“婚照地标”或具体欧陆风格作为事实。

### poi_taipa_houses — 龙环葡韵
- 变更：修改（坐标、district、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [龙环葡韵](https://www.macaotourism.gov.mo/zh-hans/step-out-macao/taipa/taipa-houses)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认五座绿色建筑、1921年前落成、原官邸和土生葡人住宅、1999年博物馆化及2016年用途整合。
  - [OpenStreetMap 对象 node/4664838891](https://www.openstreetmap.org/node/4664838891)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：删除“澳门八景”之外的宣传性比较和最佳时段承诺。

### poi_coloane_chapel — 路环圣方济各圣堂
- 变更：修改（坐标、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [路环圣方济各圣堂](https://www.macaotourism.gov.mo/zh-hans/sightseeing/churches/chapel-of-st-francis-xavier)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, name_en, intro, history, architecture, story
    - 证据摘要：确认1928年、巴洛克式处理、椭圆窗、钟楼、1910年纪念碑及圣髑移藏情况。
  - [OpenStreetMap 对象 way/229184934](https://www.openstreetmap.org/way/229184934)
    - 支持字段：coordinates, district, name_pt
- 冲突或局限：原数据称淡黄色立面；官方简中页称白色，重写为不依赖易受涂装影响的颜色描述。

### poi_coloane_pier — 路环码头
- 变更：修改（坐标、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [路环悠闲游](https://www.macaotourism.gov.mo/zh-hans/macao-full-of-fun/tranquility-tour-in-coloane-village)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：intro, history, story
    - 证据摘要：记载1873年修建、道路和大桥前的公共渡运及曾连接内地航班。
  - [OpenStreetMap 对象 way/424695938](https://www.openstreetmap.org/way/424695938)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：不写入当前航班、营业或最佳到访时段。

### poi_eanes_square — 恩尼斯总统前地
- 变更：修改（坐标、theme、全部说明文本、suitable_for）
- 来源类型：official
- 来源：
  - [路环悠闲游](https://www.macaotourism.gov.mo/zh-hans/step-out-macao/coloane)
    - 发布机构：澳门特别行政区政府旅游局
    - 访问日期：2026-07-06
    - 支持字段：intro, history, architecture, story
    - 证据摘要：说明其连接旧市区街道、纪念葡萄牙总统到访、丘比特雕像和“花园仔”社区称呼。
  - [OpenStreetMap 对象 way/241886418](https://www.openstreetmap.org/way/241886418)
    - 支持字段：coordinates, district, name_en, name_pt
- 冲突或局限：删除未核实的具体到访年份和餐饮承诺。

### poi_moorish_barracks — 海事及水务局大楼（原摩尔兵营旧址）
- 变更：新增
- 来源类型：official
- 来源：
  - [海事及水务局大楼（原摩尔兵营旧址）](https://www.wh.mo/gb/site/detail/2)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认设计者、1874年建成、原驻印警察用途、1905年用途变化及尖拱回廊建筑特征。
  - [OpenStreetMap 对象 way/667492600](https://www.openstreetmap.org/way/667492600)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_mandarin_house — 郑家大屋
- 变更：新增
- 来源类型：official
- 来源：
  - [郑家大屋](https://www.wh.mo/gb/site/detail/4)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：说明郑观应故居、1869年前建造、约4,000平方米院落、青砖中式主体与西方装饰影响。
  - [OpenStreetMap 对象 way/404235920](https://www.openstreetmap.org/way/404235920)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_st_lawrence — 圣老楞佐堂及前地（风顺堂）
- 变更：新增
- 来源类型：official
- 来源：
  - [圣老楞佐堂及前地（风顺堂）](https://www.wh.mo/gb/site/detail/5)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：记载16世纪中叶创建、1846年形成现规模、风信称谓及拉丁十字平面和高台布局。
  - [OpenStreetMap 对象 way/279952093](https://www.openstreetmap.org/way/279952093)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_st_joseph — 圣若瑟修院大楼及圣堂
- 变更：新增
- 来源类型：official
- 来源：
  - [圣若瑟修院大楼、圣堂、前地及石阶](https://www.wh.mo/gb/site/detail/6)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认1728年修院、1746至1758年圣堂、1953年修葺、巴洛克圣堂和石阶关系。
  - [OpenStreetMap 对象 relation/5828699](https://www.openstreetmap.org/relation/5828699)
    - 支持字段：coordinates, district
- 冲突或局限：修院不作为一般参观空间；英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_dom_pedro_v — 岗顶剧院
- 变更：新增
- 来源类型：official
- 来源：
  - [岗顶剧院](https://www.wh.mo/gb/site/detail/8)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：记载1860年始建、社群聚会和演出功能、电影用途及新古典希腊复兴建筑特征。
  - [OpenStreetMap 对象 way/389129455](https://www.openstreetmap.org/way/389129455)
    - 支持字段：coordinates, district
- 冲突或局限：不承诺室内开放或演出安排；英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_ho_tung_library — 何东图书馆大楼
- 变更：新增
- 来源类型：official
- 来源：
  - [何东图书馆大楼](https://www.wh.mo/gb/site/detail/9)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认1894年前建造、1918年购入、捐赠及1958年开放，并描述拱券窗、柱式、色彩与庭园。
  - [OpenStreetMap 对象 way/279957436](https://www.openstreetmap.org/way/279957436)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_st_augustine — 圣奥斯定堂
- 变更：新增
- 来源类型：official
- 来源：
  - [圣奥斯定堂](https://www.wh.mo/gb/site/detail/10)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认1591年创建、1874年重修、巡游传统、古典式立面及“龙须庙”称谓来源。
  - [OpenStreetMap 对象 way/389129453](https://www.openstreetmap.org/way/389129453)
    - 支持字段：coordinates, district
- 冲突或局限：“龙须庙”是官方记录的地方称谓故事，不外推其他传说；英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_leal_senado — 市政署大楼（原市政厅旧址）
- 变更：新增
- 来源类型：official
- 来源：
  - [市政署大楼（原市政厅旧址）](https://www.wh.mo/gb/site/detail/11)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：记载1784年建造、1874年现规模、南欧建筑特征、葡式瓷砖及1929年藏书楼。
  - [OpenStreetMap 对象 way/192573674](https://www.openstreetmap.org/way/192573674)
    - 支持字段：coordinates, district
- 冲突或局限：官方页面正文仍使用旧机构称谓“民政总署大楼”，标题与法规名已更新；采用标题现名并在括号保留旧址说明。

### poi_holy_house_mercy — 澳门仁慈堂大楼
- 变更：新增
- 来源类型：official
- 来源：
  - [澳门仁慈堂大楼](https://www.wh.mo/gb/site/detail/14)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认1569年机构创立、18世纪中叶大楼、1905年现貌、慈善职能和新古典券廊。
  - [OpenStreetMap 对象 way/265433529](https://www.openstreetmap.org/way/265433529)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_cathedral — 主教座堂（大堂）
- 变更：新增
- 来源类型：official
- 来源：
  - [主教座堂（大堂）](https://www.wh.mo/gb/site/detail/15)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：说明1622年早期教堂、19世纪重建、1937年钢筋混凝土重建、新古典立面和教区中心功能。
  - [OpenStreetMap 对象 way/330368426](https://www.openstreetmap.org/way/330368426)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_lou_kau — 卢家大屋
- 变更：新增
- 来源类型：official
- 来源：
  - [卢家大屋](https://www.wh.mo/gb/site/detail/16)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认约1889年落成、卢华绍家族、三开间三进、青砖天井和中西装饰细节。
  - [OpenStreetMap 对象 way/192573681](https://www.openstreetmap.org/way/192573681)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_st_dominic — 玫瑰圣母堂（板樟堂）
- 变更：新增
- 来源类型：official
- 来源：
  - [玫瑰圣母堂（板樟堂）](https://www.wh.mo/gb/site/detail/17)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认1587年创建、早期木板、1822年葡文报纸、古典立面与巴洛克祭坛。
  - [OpenStreetMap 对象 way/192573688](https://www.openstreetmap.org/way/192573688)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_ruins_st_paul — 大三巴牌坊
- 变更：新增
- 来源类型：official
- 来源：
  - [圣保禄学院天主之母教堂遗址](https://www.wh.mo/gb/site/detail/18)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认学院与教堂年代、1835年火灾、花岗石前壁尺寸、巴洛克与东方图像，以及“大三巴”地方称谓。
  - [OpenStreetMap 对象 way/192183185](https://www.openstreetmap.org/way/192183185)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐；不写实时开放。

### poi_na_tcha — 哪吒庙（大三巴）
- 变更：新增
- 来源类型：official
- 来源：
  - [哪吒庙（大三巴）](https://www.wh.mo/gb/site/detail/19)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认1888年创建、1901年改建、维修记录、无天井的两进式布局及澳门哪吒信仰。
  - [OpenStreetMap 对象 way/655138584](https://www.openstreetmap.org/way/655138584)
    - 支持字段：coordinates, district
- 冲突或局限：哪吒神话只作为信仰背景，不当作历史事件；英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_old_city_walls — 城墙遗迹（圣方济各斜巷一段）
- 变更：新增
- 来源类型：official
- 来源：
  - [城墙遗迹（圣方济各斜巷一段）](https://www.wh.mo/gb/site/detail/20)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：说明1569年起的筑墙史、17世纪防御体系、夯土材料与现存尺寸。
  - [OpenStreetMap 对象 node/5035380521](https://www.openstreetmap.org/node/5035380521)
    - 支持字段：coordinates, district
- 冲突或局限：英文与葡文名称已按文化局对应语种页面标题补齐。

### poi_mount_fortress — 大炮台（中央炮台）
- 变更：新增
- 来源类型：official
- 来源：
  - [大炮台（中央炮台）](https://www.wh.mo/gb/site/detail/21)
    - 发布机构：澳门特别行政区政府文化局
    - 访问日期：2026-07-06
    - 支持字段：name_zh, intro, history, architecture, story
    - 证据摘要：确认1617至1626年建造、防御和总督住所用途、约8,000平方米不规则棱堡及后续公共文化利用。
  - [OpenStreetMap 对象 way/46510080](https://www.openstreetmap.org/way/46510080)
    - 支持字段：coordinates, district
- 冲突或局限：路线强度按坡道和高差保守标为 medium；英文与葡文名称已按文化局对应语种页面标题补齐。

### 新增16项多语名称核验

> 发布机构均为澳门特别行政区政府文化局；访问日期均为2026-07-07；页面标题直接支持 `name_en` / `name_pt`。

- `poi_moorish_barracks`：[英文名称页](https://www.wh.mo/en/site/detail/2) / [葡文名称页](https://www.wh.mo/pt/site/detail/2)
- `poi_mandarin_house`：[英文名称页](https://www.wh.mo/en/site/detail/4) / [葡文名称页](https://www.wh.mo/pt/site/detail/4)
- `poi_st_lawrence`：[英文名称页](https://www.wh.mo/en/site/detail/5) / [葡文名称页](https://www.wh.mo/pt/site/detail/5)
- `poi_st_joseph`：[英文名称页](https://www.wh.mo/en/site/detail/6) / [葡文名称页](https://www.wh.mo/pt/site/detail/6)
- `poi_dom_pedro_v`：[英文名称页](https://www.wh.mo/en/site/detail/8) / [葡文名称页](https://www.wh.mo/pt/site/detail/8)
- `poi_ho_tung_library`：[英文名称页](https://www.wh.mo/en/site/detail/9) / [葡文名称页](https://www.wh.mo/pt/site/detail/9)
- `poi_st_augustine`：[英文名称页](https://www.wh.mo/en/site/detail/10) / [葡文名称页](https://www.wh.mo/pt/site/detail/10)
- `poi_leal_senado`：[英文名称页](https://www.wh.mo/en/site/detail/11) / [葡文名称页](https://www.wh.mo/pt/site/detail/11)
- `poi_holy_house_mercy`：[英文名称页](https://www.wh.mo/en/site/detail/14) / [葡文名称页](https://www.wh.mo/pt/site/detail/14)
- `poi_cathedral`：[英文名称页](https://www.wh.mo/en/site/detail/15) / [葡文名称页](https://www.wh.mo/pt/site/detail/15)
- `poi_lou_kau`：[英文名称页](https://www.wh.mo/en/site/detail/16) / [葡文名称页](https://www.wh.mo/pt/site/detail/16)
- `poi_st_dominic`：[英文名称页](https://www.wh.mo/en/site/detail/17) / [葡文名称页](https://www.wh.mo/pt/site/detail/17)
- `poi_ruins_st_paul`：[英文名称页](https://www.wh.mo/en/site/detail/18) / [葡文名称页](https://www.wh.mo/pt/site/detail/18)
- `poi_na_tcha`：[英文名称页](https://www.wh.mo/en/site/detail/19) / [葡文名称页](https://www.wh.mo/pt/site/detail/19)
- `poi_old_city_walls`：[英文名称页](https://www.wh.mo/en/site/detail/20) / [葡文名称页](https://www.wh.mo/pt/site/detail/20)
- `poi_mount_fortress`：[英文名称页](https://www.wh.mo/en/site/detail/21) / [葡文名称页](https://www.wh.mo/pt/site/detail/21)

### 坐标邻近复核

- `poi_senado` 与 `poi_holy_house_mercy` 约20.4米：仁慈堂位于议事亭前地边缘；两者由不同官方文物页和不同 OSM way 对象确认，保留为相邻但独立节点。
- `poi_na_tcha` 与 `poi_old_city_walls` 约16.4米：哪吒庙依旧城墙而建；两者由不同官方文物页及不同 OSM 对象确认，保留为相邻但独立遗产构件。

## 路线

### heritage_fullday — 历史城区纵贯一日线
- 变更：新增（替代原 heritage_fullday，并重建节点、距离、时长与标签）
- 参考线路：本项目基于已核验 POI 组合；节点总体沿澳门历史城区由南向北连续推进。
- 地图核验：[OpenStreetMap 步行路由结果](http://routing.openstreetmap.de/routed-foot/route/v1/driving/113.5312671,22.1861086;113.5323677,22.1866202;113.5344127,22.1885873;113.5350161,22.1883953;113.5367636,22.1906709;113.5373845,22.1917568;113.5382056,22.1919122;113.5383753,22.1922745;113.5399903,22.1938271;113.5403642,22.1948416;113.5408602,22.1974570;113.5406668,22.1977089;113.5405347,22.1976268;113.5422432,22.1970679?overview=false&steps=false)
- 核验日期：2026-07-06
- 核验内容：14节点顺序；返回步行距离3,438.6米、步行时间2,757秒（约46分钟）。
- 估算说明：建议停留340分钟 + 步行46分钟 + 用餐及机动约64分钟 = 450分钟。
- 风险或局限：妈阁庙、教堂、大三巴和大炮台含台阶或坡度；全程较长，宗教、办公和文化设施开放范围以现场与官方即时信息为准。

### culture_halfday — 中区建筑层次半日线
- 变更：新增（替代原 culture_halfday；重建建筑主题节点与路线参数）
- 参考线路：本项目基于已核验 POI 组合。
- 地图核验：[OpenStreetMap 步行路由结果](http://routing.openstreetmap.de/routed-foot/route/v1/driving/113.5399903,22.1938271;113.5395836,22.1932678;113.5401596,22.1937321;113.5415425,22.1934800;113.5412348,22.1942397;113.5403642,22.1948416;113.5408602,22.1974570;113.5406668,22.1977089;113.5405347,22.1976268;113.5422432,22.1970679?overview=false&steps=false)
- 核验日期：2026-07-06
- 核验内容：10节点顺序；返回步行距离1,444.2米、步行时间1,157.3秒（约19分钟）。
- 估算说明：建议停留205分钟 + 步行19分钟 + 机动约16分钟 = 240分钟。
- 风险或局限：大三巴石阶和大炮台坡道使强度高于纯平路；不得宣称无障碍。

### photo_halfday — 大三巴至望德堂摄影线
- 变更：新增（替代原 photo_halfday；消除跨向回头并重算参数）
- 参考线路：[中区世遗游](https://www.macaotourism.gov.mo/zh-hans/macao-full-of-fun/world-heritage-tour-in-central-district) 与 [望德堂文艺游](https://www.macaotourism.gov.mo/zh-hans/macao-full-of-fun/art-and-cultural-tour-in-st-lazarus-parish)；本项目只采用其中已核验节点重新组合。
- 地图核验：[OpenStreetMap 步行路由结果](http://routing.openstreetmap.de/routed-foot/route/v1/driving/113.5404425,22.1971608;113.5408602,22.1974570;113.5422432,22.1970679;113.5437742,22.1978237;113.5453660,22.1973272?overview=false&steps=false)
- 核验日期：2026-07-06
- 核验内容：5节点顺序；返回步行距离988.0米、步行时间790.3秒（约13分钟）。
- 估算说明：建议停留130分钟 + 步行13分钟 + 取景及机动约37分钟 = 180分钟。
- 风险或局限：含石阶、坡道和可能拥挤的公共空间；不承诺光线、人流或拍摄权限。

### food_family_halfday — 中区至下环饮食文化线
- 变更：新增（替代原 food_family_halfday；改为连续单向节点并重算参数）
- 参考线路：本项目基于已核验 POI 组合。
- 地图核验：[OpenStreetMap 步行路由结果](http://routing.openstreetmap.de/routed-foot/route/v1/driving/113.5399903,22.1938271;113.5376145,22.1943149;113.5345233,22.1912335?overview=false&steps=false)
- 核验日期：2026-07-06
- 核验内容：3节点顺序；返回步行距离935.2米、步行时间748.3秒（约12分钟）。
- 估算说明：建议停留120分钟 + 步行12分钟 + 用餐及机动约48分钟 = 180分钟。
- 风险或局限：街市摊档、商户营业及排队情况会变化；路线只描述街区饮食文化，不承诺具体消费点。

### taipa_hotspot_halfday — 氹仔旧城亲子观察线
- 变更：新增（替代原 taipa_hotspot_halfday；修正节点顺序、距离、强度与非法标签）
- 参考线路：[氹仔葡韵游](https://www.macaotourism.gov.mo/zh-hans/macao-full-of-fun/portuguese-ambiance-tour-at-taipa-island)
- 地图核验：[OpenStreetMap 步行路由结果](http://routing.openstreetmap.de/routed-foot/route/v1/driving/113.5569741,22.1535855;113.5587774,22.1535022;113.5597339,22.1539406?overview=false&steps=false)
- 核验日期：2026-07-06
- 核验内容：3节点顺序；返回步行距离392.5米、步行时间313.8秒（约5分钟）。
- 估算说明：建议停留125分钟 + 步行5分钟 + 用餐、休息及机动约50分钟 = 180分钟。
- 风险或局限：短距离不等于无障碍；现场坡度、展馆开放及官也街人流需即时判断。

### coloane_leisure_halfday — 路环旧市区休闲线
- 变更：主要修订（调整为单向顺序，修正距离、时长、标签、节点说明和描述）
- 参考线路：[路环悠闲游](https://www.macaotourism.gov.mo/zh-hans/macao-full-of-fun/tranquility-tour-in-coloane-village)
- 地图核验：[OpenStreetMap 步行路由结果](http://routing.openstreetmap.de/routed-foot/route/v1/driving/113.5497906,22.1190812;113.5517158,22.1179922;113.5514616,22.1169176?overview=false&steps=false)
- 核验日期：2026-07-06
- 核验内容：3节点顺序；返回步行距离486.4米、步行时间389.4秒（约6分钟）。
- 估算说明：建议停留90分钟 + 步行6分钟 + 休息及机动约54分钟 = 150分钟。
- 风险或局限：临水边缘、宗教活动和临时通行均以现场标识为准；不把路线称作实时最优。

## 待核验候选

- 福隆新街具体形成年代、“虾酱红”材料及统一骑楼类型：缺少本轮已打开的高可信具体页面支持，相关细节未写入 JSON。
- 下环街市建造年代与建筑风格：市政署文件只足以确认公共街市身份和名称，未写入未经核验的沿革。

## 文档冲突记录

- `ethics/实施清单.md` 要求 POI 增加 `source` / `license`，路线增加 `reviewed` / `verified_at`；`data/README.md` 与当前 Pydantic 模型未定义这些字段。本轮按任务优先级未扩展 JSON schema，URL 与核验日期改记在本文件。
- `plan/开发计划与清单.md` Phase 1 提议增加 `visit_duration_min` 等计算字段，但当前模型未定义。本轮未自行扩展字段。
