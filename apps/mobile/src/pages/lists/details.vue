<template>
  <view>
    <cu-custom title="词单详情" />
    <view class="detail-content">
      <view
        v-if="status === 'loading'"
        class="state-card"
        role="status"
      >
        正在加载词单…
      </view>
      <view
        v-else-if="status !== 'ready'"
        class="state-card"
        role="alert"
      >
        <view class="state-title">
          {{ status === 'missing' ? '词单不存在或已移除' : '词单加载失败' }}
        </view>
        <view class="muted">
          {{ status === 'missing' ? '可以返回词单列表，选择其他主题。' : '请检查网络后重试。' }}
        </view>
        <button
          v-if="status === 'error'"
          class="primary-button"
          @tap="loadDetails"
        >
          重新加载
        </button>
        <button
          class="secondary-button"
          @tap="toLists"
        >
          返回词单列表
        </button>
      </view>
      <template v-else>
        <view class="info-card">
          <view class="list-name">
            {{ wordList.name }}
          </view>
          <view class="author-info">
            <image
              v-if="wordList.author.avatar"
              :src="wordList.author.avatar"
              mode="aspectFill"
              class="avatar"
            />
            <text>{{ wordList.author.nickname || '词单作者' }}</text>
          </view>
          <view
            v-if="formattedDate"
            class="muted"
          >
            创建于 {{ formattedDate }}
          </view>
          <view class="description">
            {{ wordList.description || '这个词单还没有简介。' }}
          </view>
          <view class="muted">
            共 {{ wordList.words.length }} 个词 · 点击词语查看释义和发音
          </view>
        </view>
        <view
          v-if="!wordList.words.length"
          class="state-card"
        >
          <view class="state-title">
            这个词单还没有词语
          </view>
          <view class="muted">
            可以先查看其他主题词单。
          </view>
        </view>
        <button
          v-for="(word, index) in wordList.words"
          :key="word.id"
          class="word-card"
          @tap="toWordPage(word.id)"
        >
          <view class="word-heading">
            <text class="word-number">
              {{ index + 1 }}
            </text>
            <text class="word-name">
              {{ word.word }}
            </text>
            <text class="word-arrow">
              ›
            </text>
          </view>
          <view
            v-if="word.standard_pinyin || word.standard_ipa"
            class="pronunciation"
          >
            <text v-if="word.standard_pinyin">
              {{ word.standard_pinyin }}
            </text>
            <text v-if="word.standard_ipa">
              /{{ word.standard_ipa }}/
            </text>
          </view>
          <view class="definition">
            {{ word.definition || '暂无释义' }}
          </view>
        </button>
        <button
          class="secondary-button"
          @tap="toLists"
        >
          返回词单列表
        </button>
      </template>
    </view>
  </view>
</template>

<script>
import { getWordListDetails } from '@/services/lists';
import { toWordPage } from '@/routers/word';

export default {
  data() {
    return {
      id: '',
      wordList: null,
      status: 'loading',
      requestId: 0,
    };
  },
  onLoad(options) {
    this.id = options.id || '';
    this.loadDetails();
  },
  onUnload() {
    this.requestId += 1;
  },
  computed: {
    formattedDate() {
      const date = new Date(this.wordList?.createTime);
      if (Number.isNaN(date.getTime())) return '';
      return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
    },
  },
  methods: {
    async loadDetails() {
      this.requestId += 1;
      const request = this.requestId;
      if (!this.id) {
        this.status = 'missing';
        return;
      }
      this.status = 'loading';
      try {
        const response = await getWordListDetails(this.id, { background: true });
        if (request !== this.requestId) return;
        this.wordList = response;
        this.status = 'ready';
      } catch (error) {
        if (request === this.requestId) this.status = error?.statusCode === 404 ? 'missing' : 'error';
      }
    },
    toLists() {
      const pages = getCurrentPages();
      const previous = pages[pages.length - 2];
      if (previous?.route === 'pages/lists/index') {
        uni.navigateBack({ delta: 1 });
      } else {
        uni.redirectTo({ url: '/pages/lists/index' });
      }
    },
    toWordPage,
  },
};
</script>

<style scoped>
.detail-content {
  max-width: 760px;
  margin: 0 auto;
  padding: 28rpx 28rpx calc(40rpx + env(safe-area-inset-bottom));
}
.info-card, .word-card, .state-card {
  margin-bottom: 24rpx;
  padding: 32rpx;
  background: #fff;
  border-radius: 20rpx;
}
.list-name {
  font-size: 44rpx;
  font-weight: 600;
  line-height: 1.5;
  color: #202c3d;
  overflow-wrap: anywhere;
}
.author-info {
  display: flex;
  align-items: center;
  gap: 14rpx;
  margin: 24rpx 0 12rpx;
  font-size: 30rpx;
  color: #475569;
  overflow-wrap: anywhere;
}
.author-info text {
  min-width: 0;
}
.avatar {
  flex-shrink: 0;
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
}
.muted {
  font-size: 28rpx;
  line-height: 1.7;
  color: #64748b;
}
.description, .definition {
  margin-top: 20rpx;
  font-size: 32rpx;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: #334155;
}
.description {
  margin-bottom: 24rpx;
}
.word-card {
  width: 100%;
  text-align: left;
  line-height: 1.5;
}
.word-card::after {
  border: 0;
}
.word-heading {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
}
.word-number, .word-arrow {
  flex-shrink: 0;
  font-size: 28rpx;
  color: #64748b;
}
.word-name {
  flex: 1;
  min-width: 0;
  font-size: 38rpx;
  font-weight: 600;
  color: #2563a6;
  overflow-wrap: anywhere;
}
.pronunciation {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 16rpx;
  font-size: 30rpx;
  color: #64748b;
  overflow-wrap: anywhere;
}
.state-card {
  text-align: center;
  padding-top: 50rpx;
  padding-bottom: 50rpx;
}
.state-title {
  font-size: 36rpx;
  font-weight: 600;
  margin-bottom: 16rpx;
}
.primary-button, .secondary-button {
  min-height: 88rpx;
  margin-top: 28rpx;
  font-size: 30rpx;
  color: #fff;
  background: #2563a6;
}
.secondary-button {
  color: #2563a6;
  background: #fff;
}
</style>
