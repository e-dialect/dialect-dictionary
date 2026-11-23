<template>
  <view>
    <cu-custom :title="$site.shortName + '·搜索'" />
    <scroll-view
      scroll-y
      class="scrollPage"
    >
      <!--搜索栏-->
      <view class="cu-bar search bg-white">
        <view class="search-form round">
          <text class="cuIcon-search" />
          <input
            v-model="keywords"
            type="text"
            :placeholder="$site.shortName"
            :focus="true"
            confirm-type="search"
            @confirm="search($event.detail.value)"
            @input="keyFun"
          >
        </view>
        <view
          class="action"
          @tap="search()"
        >
          <text class="text-blue">
            搜索
          </text>
        </view>
      </view>

      <!--搜索类型-->
      <view class="flex bg-white">
        <view
          v-for="index in visibleScopes"
          :key="index"
          class="flex-sub text-center title"
        >
          <view
            :class="index===searchScopeIndex ? 'w_after' : 'w_active'"
            @click="checkout(index)"
          >
            {{ searchScopes[index] }}
          </view>
        </view>
      </view>

      <!-- 搜索历史 -->
      <view v-if="!searchContent">
        <view class="padding">
          <view class="margin-bottom">
            <text class="text-bold">
              搜索历史:
            </text>
          </view>
          <view
            v-if="historyList.length === 0"
            class="text-gray text-center"
          >
            <text>—— 暂时没有任何搜索记录 ——</text>
          </view>
          <view
            v-else
            class="flex flex-wrap"
          >
            <view
              v-for="(item, index) in historyList"
              :key="index"
              class="cu-btn round bg-white margin-right-xs margin-bottom-sm"
              style="height: 55upx;line-height: 55upx"
            >
              <text
                @click="searchHistory(item)"
              >
                {{ item }}
              </text>
            </view>
          </view>
          <view class="margin-top-sm text-center">
            <text
              class="text-gray cuIcon-delete"
              @click="cleanHistory"
            >
              清空历史
            </text>
          </view>
        </view>
      </view>

      <!--搜索结果-->
      <view
        v-else
      >
        <view v-if="status === 'loading'" class="padding text-center">正在查询…</view>
        <button v-else-if="status === 'error'" @tap="searchJob">加载失败，点击重试</button>
        <view v-else-if="!results.length" class="padding text-center">没有找到相关结果</view>
        <word-full-list
          v-else-if="searchScopes[searchScopeIndex]==='词语'"
          :words="results"
        />
        <character-pinyin-list
          v-else-if="searchScopes[searchScopeIndex]==='字音'"
          :characters="results"
        />
        <ArticleList
          v-else-if="searchScopes[searchScopeIndex]==='文章'"
          :article-list="results"
        />
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { searchCharacters } from '@/services/character';
import { getWords, searchWords } from '@/services/word';
import { searchArticleId, getArticles } from '@/services/article';
import { defaultMessage } from '@/services/shareMessages';
import ArticleList from '@/components/ArticleList.vue';
import WordFullList from '@/components/WordFullList.vue';
import CharacterPinyinList from '@/components/CharacterPinyinList.vue';

export default {
  components: {
    CharacterPinyinList,
    WordFullList,
    ArticleList,
  },
  data() {
    return {
      searchContent: '', // 当前搜索内容
      searchScopeIndex: 0, // 当前搜索范围序号
      searchScopes: ['词语', '字音', '文章'], // 搜索范围
      keywords: '', // 搜索关键字（输入）
      historyList: [],
      results: [],
      status: 'idle',
      requestId: 0,
    };
  },
  computed: {
    visibleScopes() {
      // Preserve the original indices used in shared links.
      return this.$featureEnabled('pinyin') ? [0, 1, 2] : [0, 2];
    },
  },
  onLoad(option) {
    const index = Number(option.index);
    if (this.visibleScopes.includes(index)) this.searchScopeIndex = index;
    try {
      const stored = JSON.parse(uni.getStorageSync('search_history'));
      if (Array.isArray(stored)) this.historyList = stored.filter(item => typeof item === 'string');
    } catch {
      this.historyList = [];
    }
    this.keywords = option.keywords || option.key || '';
    if (this.keywords) this.search();
  },
  onUnload() {
    this.requestId += 1;
  },
  /**
   * 右上角分享事件
   */
  onShareAppMessage() {
    const path = `/pages/search?index=${this.searchScopeIndex}&keywords=${encodeURIComponent(this.searchContent || this.keywords)}`;
    return {
      title: `${this.$site.shortName}·搜索：${this.keywords}`,
      path,
      ...defaultMessage(),
    };
  },
  methods: {
    /**
     * 调整历史记录显示
     */
    keyFun(event) {
      this.keywords = event.detail.value;
      if (!event.detail.value.trim()) {
        this.requestId += 1;
        this.searchContent = '';
        this.results = [];
      }
    },

    /**
     * 从历史记录中搜索
     * @param item 历史记录项
     */
    searchHistory(item) {
      this.keywords = item;
      this.search();
    },

    /**
     * 搜索
     */
    search(value = this.keywords) {
      const term = value.trim();
      if (!term) {
        uni.showToast({ title: '请输入搜索内容', icon: 'none' });
        return;
      }
      this.searchContent = term;
      this.historyList = [term, ...this.historyList.filter(item => item !== term)];
      uni.setStorageSync('search_history', JSON.stringify(this.historyList));
      this.searchJob();
    },

    checkout(index) {
      if (index === this.searchScopeIndex) return;
      this.searchScopeIndex = index;
      if (this.searchContent) this.searchJob();
    },

    async searchJob() {
      const request = ++this.requestId;
      const term = this.searchContent;
      const scope = this.searchScopes[this.searchScopeIndex];
      this.results = [];
      this.status = 'loading';
      try {
        let rows;
        if (scope === '词语') {
          const { words } = await searchWords(term, { background: true });
          if (request !== this.requestId) return;
          rows = words.length ? (await getWords(words, { background: true })).words : [];
        } else if (scope === '文章') {
          const { articles } = await searchArticleId(term, { background: true });
          if (request !== this.requestId) return;
          rows = articles.length ? (await getArticles(articles, { background: true })).articles : [];
        } else {
          rows = (await searchCharacters(term, { background: true })).characters;
        }
        if (request === this.requestId) {
          this.results = rows;
          this.status = 'ready';
        }
      } catch {
        if (request === this.requestId) this.status = 'error';
      }
    },

    /**
     * 清空历史记录
     */
    cleanHistory() {
      if (this.historyList.length === 0) {
        uni.showToast({
          icon: 'none',
          title: '没有任何搜索记录',
        });
      } else {
        uni.showModal({
          content: '确定要清空全部历史记录吗？',
          success: (res) => {
            if (res.confirm) {
              uni.removeStorage({
                key: 'search_history',
              });
              this.historyList = [];
            }
          },
        });
      }
    },
  },
};
</script>

<style scoped>
.title {
width: 530rpx;
height: 78rpx;
margin: auto;
justify-content: space-between;
margin-top: 47rpx;
color: #7F7F7F;
font-size: 40rpx;
font-weight: bold;
text-align: center;
}

.w_after {
color: #212121;
}

.w_after::after {
content: ' ';
display: block;
width: 28rpx;
height: 6rpx;
background: #2B87FF;
border-radius: 3rpx;
margin: auto;
}
</style>
