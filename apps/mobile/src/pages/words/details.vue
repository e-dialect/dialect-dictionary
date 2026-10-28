<template>
  <view
    @touchstart="start"
    @touchend="end"
  >
    <!--导航栏-->
    <cu-custom :back-home="true" />

    <!--标题栏：词语-->
    <view class="flex padding solid-bottom">
      <view class="flex-sub">
        <view
          class="text-bold text-sl"
          @longpress="setClipboard(word.word)"
        >
          {{ word.word }}
        </view>
      </view>
      <view class="flex-sub">
        <view class="text-grey text-df">
          访问：{{ word.views }}
        </view>
        <view class="text-grey text-df margin-top-xs">
          来源：
          <text
            :data-id="word.contributor.id"
            class="text-blue"
            @tap="toUserPage(word.contributor.id)"
          >
            {{ word.contributor.nickname }}
          </text>
        </view>
      </view>
    </view>

    <!--标题栏：发音-->
    <view class="padding solid-bottom flex align-center">
      <view class="flex-twice">
        <view>
          <text
            class="text-bold text-xl"
            space="ensp"
            @longpress="setClipboard(word.standard_pinyin)"
          >
            {{ word.standard_pinyin }}
          </text>
          <WordPronunciationButton
            v-if="!word.source"
            :pinyin="word.standard_pinyin"
            :word-id="id"
          />
        </view>
        <view>
          <text
            class="text-grey text-xl"
            space="ensp"
            @longpress="setClipboard(word.standard_ipa)"
          >
            /{{ word.standard_ipa }}/
          </text>
          <WordPronunciationButton
            :ipa="word.standard_ipa"
            :source="word.source"
            :word-id="id"
          />
        </view>
      </view>
      <view class="flex-sub">
        <button
          class="cu-btn round bg-gradual-blue shadow"
          @tap="toUploadPronunciationPage(id)"
        >
          我来发音
        </button>
        <button
          v-if="pronunciation.length !== 0"
          class="cu-btn round bg-gradual-blue shadow margin-top-xs"
          @tap="toWordPronunciations(word.id)"
        >
          查看语音
        </button>
      </view>
    </view>

    <!--词语内容-->
    <scroll-view
      :scroll-y="true"
      style="min-height: 95vh"
      class="margin"
    >
      <!--释义-->
      <view>
        <view class="text-bold text-xl">
          释义
        </view>
        <view
          v-for="(item, index) in word.definitions"
          :key="index"
          class="margin-top-sm margin-left-sm"
          style="width: 90vw"
        >
          <text
            class="text-xl"
            @longpress="setClipboard(item.content)"
          >
            {{ item.content }}
          </text>
          <view
            v-for="(jtem, index1) in item.example"
            :key="index1"
            class="padding-sm"
            @longpress="copyExample(jtem)"
          >
            <uni-tag
              style="width: 8vw"
              :text="jtem.type"
              :type="jtem.type==='例'?'error':'warning'"
              :inverted="true"
              size="small"
              @click="copyExample(jtem)"
            />
            <text class="margin-left-sm">
              {{ jtem.content }}
            </text>
            <text class="text-grey">
              {{ jtem.explain }}
            </text>
          </view>
        </view>

        <!--相关词汇-->
        <view
          v-if="word.related_words.length !== 0"
          class="margin-top-xl"
        >
          <view class="text-bold text-xl">
            相关词汇
          </view>
          <view class="margin-top-sm margin-lr-sm">
            <text
              v-for="(item, index) in word.related_words"
              :key="index"
              class="text-blue"
              @tap="toWordPage(item.id)"
            >
              {{ item.word + " " }}
            </text>
          </view>
        </view>
      </view>

      <!--普通话词汇-->
      <view
        v-if="word.mandarin.length !== 0"
        class="margin-top-xl"
      >
        <view class="text-bold text-xl">
          普通话词汇
        </view>
        <view class="margin-top-sm margin-left-sm ">
          <text
            v-for="(item, index) in word.mandarin"
            :key="index"
          >
            {{ item + " " }}
          </text>
        </view>
      </view>

      <!--附注-->
      <view
        v-if="word.annotation.length !== 0"
        class="margin-top-xl"
      >
        <view class="text-bold text-xl">
          附注
        </view>
        <view class="margin-top-sm margin-lr-sm">
          <MarkdownViewer
            style="max-width: 90%"
            :markdown="word.annotation"
          />
        </view>
      </view>

      <!--相关文章-->
      <view
        v-if="word.related_articles.length"
        class="margin-top-xl"
      >
        <view class="text-bold text-xl">
          相关文章
        </view>
        <view class="margin-top-sm margin-left-sm  cu-list">
          <view
            v-for="(item, index) in word.related_articles"
            :key="index"
            class="cu-item text-blue margin"
            @tap="toArticlePage(item.id)"
          >
            {{ item.title }}
          </view>
        </view>
      </view>

      <!--词条贡献入口-->
      <view class="text-gray text-sm margin-top-xl margin-bottom-lg">
        <view class="margin-bottom-sm">内容有误或想补充？提交申请，由管理员审核更新。</view>
        <button class="cu-btn bg-blue margin-right-sm" @tap="toWordEditPage(id)">纠错申请</button>
        <button class="cu-btn line-blue" @tap="toWordEditPage(0)">贡献新词</button>
        <view class="margin-top-sm">
          也可以
          <text class="text-blue cuIcon-link" @tap="toTuxiaochaoPage()">反馈</text>
          给管理员。
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { getWordDetails } from '@/services/word';
import { toLoginPage } from '@/routers/login';
import { playAudio } from '@/utils/audio';
import { getPronunciations } from '@/services/pronunciation';
import { toUploadPronunciationPage, toWordPage, toWordPronunciations } from '@/routers/word';
import { toUserPage } from '@/routers/user';
import { defaultMessage } from '@/services/shareMessages';
import { toTuxiaochaoPage } from '@/routers';
import { toArticlePage } from '@/routers/article';
import { setClipboard } from '@/utils/clipboard';
import MarkdownViewer from '@/components/MarkdownViewer.vue';
import WordPronunciationButton from '@/components/WordPronunciationButton.vue';

export default {
  components: { MarkdownViewer, WordPronunciationButton },
  data() {
    return {
      id: 0,
      word: {
        id: 0,
        word: '',
        definition: '',
        definitions: [],
        contributor: {
          nickname: '',
          avatar: '',
          id: 0,
        },
        annotation: '',
        mandarin: [],
        related_words: [],
        related_articles: [],
        views: 0,
        standard_ipa: '',
        standard_pinyin: '',
        source: '',
      },
      startData: { clientX: 0, clientY: 0 },
      pronunciation: [],
    };
  },

  /**
   * 右上角分享事件
   */
  onShareAppMessage() {
    let title = `${this.word.word}：`;
    this.word.definitions.forEach((item) => {
      title += `${item.content}；`;
    });
    return {
      title,
      path: `/pages/words/details?id=${this.id}`,
      ...defaultMessage(),
    };
  },

  /**
   * 生命周期函数--监听页面加载
   * @param options
   */
  async onLoad(options) {
    uni.pageScrollTo({
      scrollTop: 0,
      duration: 0,
    });
    this.id = options.id;
    this.word = await getWordDetails(options.id);
    this.word = { ...this.word };
    this.pronunciation = await getPronunciations({ word: options.id });
  },
  methods: {
    toUploadPronunciationPage,
    playAudio,
    toUserPage,
    toWordPage,
    toWordPronunciations,
    setClipboard,
    toArticlePage,
    toTuxiaochaoPage,
    toWordEditPage(wordId) {
      if (!uni.getStorageSync('token') || !uni.getStorageSync('id')) {
        uni.showToast({ title: '请先登录后提交申请', icon: 'none' });
        toLoginPage();
        return;
      }
      uni.navigateTo({ url: `/pages/words/edit?id=${wordId}` });
    },
    copyExample(example) {
      let str = `${example.type}：${example.content}`;
      if (example.explain) {
        str += `（${example.explain}）`;
      }
      setClipboard(str);
    },
    start(e) {
      this.startData.clientX = e.changedTouches[0].clientX;
      this.startData.clientY = e.changedTouches[0].clientY;
    },
    end(e) {
      const subX = e.changedTouches[0].clientX - this.startData.clientX;
      // const subY = e.changedTouches[0].clientY - this.startData.clientY;
      if (subX > 50) {
        uni.navigateBack();
      } else if (subX < -50) {
        const randomId = Math.floor(Math.random() * 6099) + 1;
        toWordPage(randomId);
      }
    },
  },
};
</script>
<style>
page {
  background-color: #ffffff;
}
</style>
