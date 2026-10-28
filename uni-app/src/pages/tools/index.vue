<template>
  <view>
    <cu-custom
      title="语记·工具"
      :is-back="false"
    />
    <scroll-view
      scroll-y
      style="height: 100%"
    >
      <view
        class="cu-card"
        style="margin-bottom: 120upx;"
      >
        <view
          v-for="(item, index) in list.filter(tool => pageEnabled(tool.url))"
          :key="index"
          :data-url="item.url"
          class="cu-item bg-white shadow-blur"
          style="height: 15vh"
          @tap="getTools"
        >
          <view class="cardTitle text-blue">
            {{ item.label }}
          </view>
        </view>
      </view>
      <view class="stand-view" />
    </scroll-view>
  </view>
</template>

<script>
import { pageEnabled } from '@/config/features';
import { defaultMessage } from '@/services/shareMessages';

export default {
  data() {
    return {
      list: [
        {
          label: '拼音方案',
          url: '/tools/pinyin',
        },
        {
          label: '音序查词',
          url: '/tools/dictionary',
        },
        {
          label: '词单学习',
          url: '/lists/index',
        },

        {
          label: '方言测试',
          url: '/quizzes/index',
        },
        {
          label: '条件查字',
          url: '/tools/condition',
        },
        {
          label: '日常用语',
          url: '/tools/daily-expression/index',
        },
        {
          label: '贡献排行',
          url: '/words/pronunciations/ranking',
        },
        {
          label: '亲属计算',
          url: '/tools/relative',
        },
      ],
    };
  },
  options: {
    addGlobalClass: true,
  },
  onShareAppMessage() {
    return {
      title: '语记·工具',
      path: '/pages/tools/index',
      ...defaultMessage(),
    };
  },
  methods: {
    pageEnabled,
    getTools(e) {
      uni.navigateTo({
        url: `/pages${e.currentTarget.dataset.url}`,
      });
    },
  },
};
</script>
<style>
.cardTitle {
  color: #fff;
  padding: 90rpx 60rpx;
  font-size: 40rpx;
  font-weight: 300;
  transform: skew(-10deg, 0deg);
  position: relative;
  text-shadow: 0px 0px 6rpx rgba(0, 0, 0, 0.3);
}

</style>
