import { featureEnabled } from './site'
const routes = {
  Pinyin: 'pinyin',
  Dictionary: 'pinyin',
  Conditions: 'pinyin',
  Characters: 'pinyin',
  Relative: 'kinship',
  Music: 'music',
  DailyExpressions: 'dailyExpressions',
  PuxianExam: 'quiz',
  QuizCreate: 'quiz',
  QuizDetails: 'quiz',
  QuizResearch: 'quiz',
  Certificate: 'quiz',
  Translation: 'translation',
  ptxTranslation: 'translation',
  xtpTranslation: 'translation'
}
export const routeEnabled = name => !routes[name] || featureEnabled(routes[name])
