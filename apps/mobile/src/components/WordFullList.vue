<template>
  <view class="cu-list menu">
    <view
      v-for="(item, index1) in words"
      :key="item.word.id"
      class="cu-item arrow"
      style="min-height: 240rpx;border-bottom: 1upx solid rgba(0, 0, 0, 0.07);"
      :data-index="index1"
      @tap="toWordPage(item.word.id)"
    >
      <view class="flex flex-direction justify-between">
        <view class="margin-bottom-xs">
          <text class="text-xxl text-bold">
            {{ item.word.word }}
          </text>
        </view>
        <view
          class="margin-bottom-xs"
        >
          <text>{{ item.word.standard_pinyin }}</text>
          <text class="text-grey padding-left">
            /{{ item.word.standard_ipa }}/
          </text>
          <WordPronunciationButton :source="item.pronunciation.url" />
        </view>
        <view class="text-grey definition">
          {{ item.word.definition }}
        </view>
      </view>
    </view>
    <view
      v-if="words.length === 0"
      class="text-center margin"
    >
      <text class="text-lg text-gray">
        --- 暂无数据 ---
      </text>
    </view>
  </view>
</template>
<script>

import { toWordPage } from '@/routers/word';
import WordPronunciationButton from '@/components/WordPronunciationButton.vue';

export default {
  name: 'WordFullList',
  components: { WordPronunciationButton },
  props: {
    words: {
      type: Array,
      default: () => [],
    },
  },
  methods: { toWordPage },
};
</script>

<style scoped>
.definition{
  overflow: hidden;
  -webkit-line-clamp: 2;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
}
</style>
