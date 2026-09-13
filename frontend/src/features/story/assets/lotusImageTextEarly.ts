import type { LanguageCode } from "@/types";

// Transcriptions and translations of legible text in the story illustrations.
export const LOTUS_IMAGE_TEXT_EARLY: Record<string, Record<LanguageCode, string[]>> = {
  "V4-AMA-03": {
    "zh-CN": ["城市测绘图　M", "莲城脉图　阿澜"],
    "zh-TW": ["城市測繪圖　M", "蓮城脈圖　阿瀾"],
    en: ["City Survey Map · M", "Map of the Lotus City’s Pulse · A Lan"],
    pt: ["Mapa Topográfico da Cidade · M", "Mapa do Pulsar da Cidade de Lótus · A Lan"],
  },
  "V4-AMA-04": {
    "zh-CN": [
      "去找一个在城名以前已经被记住的地方。",
      "山不离海，香不离风。",
      "不要先找正确的海岸，先找比海岸更不容易移动的东西。",
    ],
    "zh-TW": [
      "去找一個在城名以前已經被記住的地方。",
      "山不離海，香不離風。",
      "不要先找正確的海岸，先找比海岸更不容易移動的東西。",
    ],
    en: [
      "Find a place that was remembered before the city had its name.",
      "The hill stays by the sea; incense stays with the wind.",
      "Do not begin by looking for the correct shoreline. First find something less likely to move than the shore.",
    ],
    pt: [
      "Procure um lugar de que já se guardava memória antes de a cidade ter nome.",
      "A colina não se afasta do mar; o incenso não se afasta do vento.",
      "Não comece por procurar a linha de costa correta. Procure primeiro algo que mude de lugar com menos facilidade do que a costa.",
    ],
  },
  "V4-MAN-04": {
    "zh-CN": [
      "我曾问M先生，一座屋应该怎样画。",
      "梁上有木，天井有火，院心有土，门上有金。",
      "找到前四处，把这张纸放正。最后一个空孔落在哪里，那里就是M先生没有写下的第五行。",
      "第五样不在房间里，它藏在两座屋都不愿占去的地方。",
    ],
    "zh-TW": [
      "我曾問M先生，一座屋應該怎樣畫。",
      "梁上有木，天井有火，院心有土，門上有金。",
      "找到前四處，把這張紙放正。最後一個空孔落在哪裡，那裡就是M先生沒有寫下的第五行。",
      "第五樣不在房間裡，它藏在兩座屋都不願佔去的地方。",
    ],
    en: [
      "I once asked Mr. M how a house should be drawn.",
      "Wood in the beams, fire in the skywell, earth at the heart of the courtyard, metal on the door.",
      "Find the first four places and align this sheet. Wherever the last empty hole falls, there lies the fifth element Mr. M left unwritten.",
      "The fifth thing is not inside a room. It is hidden in a place neither house wishes to occupy.",
    ],
    pt: [
      "Perguntei uma vez ao Sr. M como se deveria desenhar uma casa.",
      "Há madeira nas vigas, fogo no pátio de luz, terra no centro do pátio e metal na porta.",
      "Encontra os primeiros quatro lugares e alinha esta folha. Onde ficar o último orifício vazio, aí estará o quinto elemento que o Sr. M não escreveu.",
      "A quinta coisa não está dentro de uma divisão. Esconde-se num lugar que nenhuma das duas casas deseja ocupar.",
    ],
  },
  "V4-MAN-05": {
    "zh-CN": ["空白不是错误，但空白也应该有人解释。"],
    "zh-TW": ["空白不是錯誤，但空白也應該有人解釋。"],
    en: ["A blank space is not a mistake, but someone should still explain it."],
    pt: ["Um espaço em branco não é um erro, mas também merece que alguém o explique."],
  },
  "V4-SEN-04": {
    "zh-CN": [
      "我只能画下自己见过的城。",
      "如果你在许多年后来到这里，不要先问旧地图漏画了什么。",
      "先站在原处看看：这座城在我离开以后，又给这里添上了什么。",
      "找出两样我不可能见过的东西，再问问今天的人怎样称呼这里。",
    ],
    "zh-TW": [
      "我只能畫下自己見過的城。",
      "如果你在許多年後來到這裡，不要先問舊地圖漏畫了什麼。",
      "先站在原處看看：這座城在我離開以後，又給這裡添上了什麼。",
      "找出兩樣我不可能見過的東西，再問問今天的人怎樣稱呼這裡。",
    ],
    en: [
      "I can only draw the city I have seen.",
      "If you come here many years later, do not begin by asking what the old map left out.",
      "First stand in the same spot and look: what has the city added here since I left?",
      "Find two things I could not possibly have seen, then ask the people of today what they call this place.",
    ],
    pt: [
      "Só posso desenhar a cidade que vi.",
      "Se vieres aqui muitos anos depois, não comeces por perguntar o que falta no mapa antigo.",
      "Primeiro, fica no mesmo lugar e observa: o que acrescentou a cidade a este lugar depois de eu partir?",
      "Encontra duas coisas que eu não poderia ter visto e pergunta às pessoas de hoje como chamam a este lugar.",
    ],
  },
};
