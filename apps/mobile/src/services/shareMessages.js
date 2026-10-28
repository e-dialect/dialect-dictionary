import siteConfig from '@/config/site';

export function message(successMessage, failMessage) {
  return {
    success() {
      uni.showToast({
        title: successMessage,
        icon: 'success',
      });
    },
    fail() {
      uni.showToast({
        title: failMessage,
        icon: 'error',
      });
    },
  };
}

export function defaultMessage() {
  // WeChat share hooks do not confirm delivery to the recipient.
  return {};
}
export default {
  // #ifdef MP-WEIXIN
  onShareTimeline() {
    return {
      title: siteConfig.name,
      imageUrl: siteConfig.logo,
      ...defaultMessage(),
    };
  },
  // #endif
};
