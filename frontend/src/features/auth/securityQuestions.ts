import type { LanguageCode } from "@/types";

export const SECURITY_QUESTIONS = [
  {
    id: "childhood_friend",
    label: {
      "zh-CN": "你童年最好朋友的名字是什么？",
      "zh-TW": "你童年最好朋友的名字是甚麼？",
      en: "What was the name of your childhood best friend?",
      pt: "Qual era o nome do seu melhor amigo de infância?",
    },
  },
  {
    id: "first_school",
    label: {
      "zh-CN": "你就读的第一所学校叫什么？",
      "zh-TW": "你就讀的第一所學校叫甚麼？",
      en: "What was the name of your first school?",
      pt: "Qual era o nome da sua primeira escola?",
    },
  },
  {
    id: "favorite_place",
    label: {
      "zh-CN": "你小时候最喜欢的地方是哪里？",
      "zh-TW": "你小時候最喜歡的地方是哪裡？",
      en: "What was your favorite place as a child?",
      pt: "Qual era o seu lugar favorito em criança?",
    },
  },
  {
    id: "childhood_nickname",
    label: {
      "zh-CN": "你小时候的昵称是什么？",
      "zh-TW": "你小時候的暱稱是甚麼？",
      en: "What was your childhood nickname?",
      pt: "Qual era a sua alcunha de infância?",
    },
  },
] as const satisfies ReadonlyArray<{
  id: string;
  label: Record<LanguageCode, string>;
}>;

export function securityQuestionLabel(questionId: string, language: LanguageCode): string {
  const question = SECURITY_QUESTIONS.find((item) => item.id === questionId);
  return question?.label[language] ?? question?.label.en ?? questionId;
}
