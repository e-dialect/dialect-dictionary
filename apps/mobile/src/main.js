import { createSSRApp } from 'vue';
import siteConfig, { featureEnabled } from '@/config/site';
import { installFeatureGuards } from '@/config/features';
import share from '@/services/shareMessages';

// 全局mixins，用于实现setData等功能，请勿删除！';
import Mixin from '@/polyfill/mixins';
import App from './App.vue';

// Use native uni APIs; unsupported capabilities must not receive fabricated success callbacks.

// 不能修改导出的 createApp 方法名，不能修改从 Vue 中导入的 createSSRApp。
// eslint-disable-next-line import/prefer-default-export
export function createApp() {
  const app = createSSRApp(App);
  app.config.globalProperties.$site = siteConfig;
  app.config.globalProperties.$featureEnabled = featureEnabled;
  installFeatureGuards(app);
  app.mixin(Mixin);
  app.mixin(share);
  return {
    app,
  };
}
