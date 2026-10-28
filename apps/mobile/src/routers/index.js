import siteConfig, { featureEnabled } from '@/config/site';

/**
 * 跳转至首页
 */
export function toIndexPage(closeAll = false) {
  if (closeAll) {
    uni.reLaunch({
      url: '/pages/index',
    });
  } else {
    uni.navigateTo({
      url: '/pages/index',
    });
  }
}

/**
 * 前往搜索页面
 */
export function toSearchPage() {
  uni.navigateTo({
    url: '/pages/search',
  });
}

/** Open the explicitly configured deployment feedback channel. */
export function toTuxiaochaoPage() {
  const { feedback } = siteConfig;
  const unavailable = () => uni.showModal({
    title: '联系词典运营者',
    content: '本实例未配置外部反馈渠道，请联系本词典运营者。',
    showCancel: false,
  });
  if (!featureEnabled('legacyLinks') || !feedback) {
    unavailable();
    return;
  }
  const platform = uni.getSystemInfoSync().uniPlatform;
  if (platform === 'web' && feedback.webUrl && /^https?:\/\//.test(feedback.webUrl)) {
    // #ifdef H5
    window.location.assign(feedback.webUrl);
    // #endif
    return;
  }
  // #ifdef MP-WEIXIN
  if (platform === 'mp-weixin' && feedback.miniProgramAppId && feedback.productId) {
    const options = {
      appId: feedback.miniProgramAppId,
      extraData: { id: feedback.productId },
      fail() {
        uni.showToast({ title: '跳转失败', icon: 'none' });
      },
    };
    const fallback = () => uni.navigateToMiniProgram(options);
    if (typeof uni.openEmbeddedMiniProgram === 'function') {
      uni.openEmbeddedMiniProgram({ ...options, fail: fallback });
    } else fallback();
    return;
  }
  // #endif
  unavailable();
}
