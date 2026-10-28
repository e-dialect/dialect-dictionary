import { featureEnabled } from './site';

export function pageFeature(path) {
  if (/\/tools\/(pinyin|dictionary|condition)|\/words\/characters/.test(path)) return 'pinyin';
  if (/\/tools\/relative/.test(path)) return 'kinship';
  if (/\/tools\/daily-expression/.test(path)) return 'dailyExpressions';
  if (/\/quizzes/.test(path)) return 'quiz';
  if (/\/music/.test(path)) return 'music';
  return '';
}
export function pageEnabled(path) {
  const feature = pageFeature(path);
  return !feature || featureEnabled(feature);
}
export function installFeatureGuards(app) {
  ['navigateTo', 'redirectTo', 'reLaunch', 'switchTab'].forEach((method) => {
    uni.addInterceptor(method, {
      invoke(args) {
        if (!pageEnabled(args.url)) {
          uni.showToast({ title: '本词典未启用此功能', icon: 'none' });
          return false;
        }
        return true;
      },
    });
  });
  app.mixin({
    onLoad() {
      const pages = getCurrentPages();
      const page = pages[pages.length - 1];
      if (page && !pageEnabled(`/${page.route}`)) uni.reLaunch({ url: '/pages/index' });
    },
  });
}
