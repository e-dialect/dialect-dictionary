<template>
  <view class="lists-page">
    <cu-custom :title="$site.shortName + '·词单'" />
    <view class="page-content">
      <view class="intro-card">
        <view class="section-heading">
          <text class="page-title">
            词单学习
          </text>
          <button
            class="small-button"
            :disabled="loading"
            @tap="loadLists"
          >
            {{ loading ? '加载中…' : '刷新' }}
          </button>
        </view>
        <view class="intro-text">
          按主题认识{{ $site.dialect.name }}词语，打开词单开始学习。
        </view>
        <view
          v-if="status === 'ready'"
          class="muted"
        >
          共 {{ lists.length }} 个词单
        </view>
      </view>
      <view
        v-if="status === 'loading'"
        class="state-card"
        role="status"
      >
        正在加载词单…
      </view>
      <view
        v-else-if="status === 'error'"
        class="state-card"
        role="alert"
      >
        <view class="state-title">
          词单加载失败
        </view>
        <view class="muted">
          请检查网络后重试。
        </view>
        <button
          class="primary-button"
          @tap="loadLists"
        >
          重新加载
        </button>
      </view>
      <view
        v-else-if="!lists.length"
        class="state-card"
      >
        <view class="state-title">
          还没有词单
        </view>
        <view class="muted">
          可以先查词，或创建一个主题词单。
        </view>
        <button
          class="primary-button"
          @tap="toSearchPage"
        >
          去查词
        </button>
      </view>
      <template v-else>
        <button
          v-for="list in lists"
          :key="list.id"
          class="list-card"
          @tap="viewList(list.id)"
        >
          <view class="section-heading">
            <text class="list-title">
              {{ list.name }}
            </text>
            <text class="word-count">
              {{ list.length }} 个词
            </text>
          </view>
          <view class="list-description">
            {{ list.description || '这个词单还没有简介。' }}
          </view>
          <view class="list-meta">
            <text>{{ list.author.nickname || '词单作者' }}</text>
            <text>查看词单 ›</text>
          </view>
        </button>
        <view class="end-note">
          已显示全部词单
        </view>
      </template>
      <button
        class="create-button"
        @tap="createList"
      >
        创建词单
      </button>
    </view>
  </view>
</template>

<script>
import { getWordLists } from '@/services/lists';
import { toSearchPage } from '@/routers';

export default {
  data() {
    return {
      lists: [],
      status: 'loading',
      loading: false,
      requestId: 0,
    };
  },
  onLoad() {
    this.loadLists();
  },
  onPullDownRefresh() {
    this.loadLists();
  },
  onUnload() {
    this.requestId += 1;
  },
  methods: {
    toSearchPage,
    async loadLists() {
      if (this.loading) {
        uni.stopPullDownRefresh();
        return;
      }
      this.requestId += 1;
      const request = this.requestId;
      this.loading = true;
      this.status = 'loading';
      try {
        const response = await getWordLists({ background: true });
        if (request !== this.requestId) return;
        this.lists = response.lists;
        this.status = 'ready';
      } catch {
        if (request === this.requestId) this.status = 'error';
      } finally {
        if (request === this.requestId) this.loading = false;
        uni.stopPullDownRefresh();
      }
    },
    viewList(id) {
      uni.navigateTo({ url: `/pages/lists/details?id=${encodeURIComponent(id)}` });
    },
    createList() {
      uni.navigateTo({ url: '/pages/lists/upload' });
    },
  },
};
</script>

<style scoped>
.page-content {
  max-width: 760px;
  margin: 0 auto;
  padding: 28rpx 28rpx calc(40rpx + env(safe-area-inset-bottom));
}
.intro-card, .state-card, .list-card {
  padding: 32rpx;
  margin-bottom: 24rpx;
  background: #fff;
  border-radius: 20rpx;
}
.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20rpx;
}
.page-title, .state-title {
  font-size: 38rpx;
  font-weight: 600;
  color: #202c3d;
}
.intro-text, .list-description {
  margin: 20rpx 0;
  font-size: 30rpx;
  line-height: 1.7;
  color: #475569;
  overflow-wrap: anywhere;
}
.muted, .list-meta, .end-note {
  color: #64748b;
  font-size: 28rpx;
  line-height: 1.6;
}
.state-card {
  text-align: center;
  padding-top: 50rpx;
  padding-bottom: 50rpx;
}
.state-title {
  margin-bottom: 16rpx;
}
.small-button {
  flex-shrink: 0;
  margin: 0;
  padding: 0 24rpx;
  min-height: 80rpx;
  line-height: 80rpx;
  font-size: 28rpx;
  color: #2563a6;
  background: #eef5ff;
}
.list-card {
  width: 100%;
  text-align: left;
  line-height: 1.5;
}
.list-card::after, .small-button::after {
  border: 0;
}
.list-title {
  flex: 1;
  min-width: 0;
  font-size: 36rpx;
  font-weight: 600;
  color: #202c3d;
  overflow-wrap: anywhere;
}
.word-count {
  flex-shrink: 0;
  color: #2563a6;
  font-size: 26rpx;
  padding: 6rpx 12rpx;
  background: #eef5ff;
  border-radius: 10rpx;
}
.list-description {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.list-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12rpx;
  overflow-wrap: anywhere;
}
.primary-button, .create-button {
  margin-top: 28rpx;
  min-height: 88rpx;
  font-size: 30rpx;
  color: #fff;
  background: #2563a6;
}
.create-button {
  color: #2563a6;
  background: #fff;
}
.end-note {
  text-align: center;
  margin: 30rpx 0;
}
</style>
