<template>
  <view class="word-application">
    <cu-custom :title="id ? '词条纠错申请' : '贡献新词'" />
    <view
      v-if="authRequired"
      class="padding"
    >
      <view class="margin-bottom">
        登录后即可提交词条申请。
      </view>
      <button
        class="cu-btn bg-blue"
        @tap="toLoginPage"
      >
        前往登录
      </button>
    </view>
    <view
      v-else-if="loading"
      class="padding text-grey"
    >
      正在加载词条…
    </view>
    <view
      v-else-if="loadError"
      class="padding"
    >
      <view class="text-red margin-bottom">
        {{ loadError }}
      </view>
      <button
        v-if="!invalidId"
        class="cu-btn"
        @tap="loadWord"
      >
        重新加载
      </button>
    </view>
    <view
      v-else-if="!capabilityAllowed"
      class="padding"
    >
      <view class="margin-bottom">
        本实例暂未开放词条申请，或当前无法确认服务状态。
      </view>
      <button
        class="cu-btn"
        @tap="loadWord"
      >
        重新检查
      </button>
    </view>
    <view
      v-else-if="submitted"
      class="padding"
    >
      <view class="text-xl text-bold margin-bottom">
        申请已提交，等待审核
      </view>
      <view>审核通过后词条内容才会更新，请勿重复提交。</view>
      <view
        v-if="applicationId"
        class="margin-top"
      >
        申请编号：{{ applicationId }}
      </view>
      <button
        class="cu-btn bg-blue margin-top"
        @tap="leave"
      >
        返回
      </button>
    </view>
    <view
      v-else-if="loaded"
      class="padding"
    >
      <view class="notice padding margin-bottom">
        {{ id ? '提交纠错申请后，由管理员审核更新词条。' : '感谢贡献新词，提交后由管理员审核发布。' }}
      </view>
      <view class="field">
        <view class="field-label">
          词条名称 *
        </view>
        <input
          v-model="draft.word"
          :maxlength="60"
          class="field-input"
          placeholder="填写词条名称"
          :disabled="submitting"
        >
      </view>
      <view class="field">
        <view class="field-label">
          拼音
        </view>
        <input
          v-model="draft.standard_pinyin"
          :maxlength="30"
          class="field-input"
          placeholder="可留空，在申请说明中注明"
          :disabled="submitting"
        >
      </view>
      <view class="field">
        <view class="field-label">
          国际音标 IPA
        </view>
        <input
          v-model="draft.standard_ipa"
          :maxlength="30"
          class="field-input"
          placeholder="可留空"
          :disabled="submitting"
        >
      </view>
      <view class="field">
        <view class="field-label">
          释义 *
        </view>
        <textarea
          v-model="draft.definition"
          :maxlength="-1"
          class="field-textarea"
          auto-height
          placeholder="填写释义和例句"
          :disabled="submitting"
        />
        <view class="text-grey text-sm margin-top-xs">
          修改时请保留已有的①②、全角冒号及例句格式。不确定的内容可在申请说明中注明。
        </view>
      </view>
      <view class="field">
        <view class="field-label">
          普通话对应词（每行一个）
        </view>
        <textarea
          v-model="draft.mandarinText"
          :maxlength="-1"
          class="field-textarea"
          auto-height
          placeholder="每行填写一个对应词"
          :disabled="submitting"
        />
      </view>
      <view class="field">
        <view class="field-label">
          标签（每行一个）
        </view>
        <textarea
          v-model="draft.tagsText"
          :maxlength="-1"
          class="field-textarea"
          auto-height
          placeholder="可留空"
          :disabled="submitting"
        />
      </view>
      <view class="field">
        <view class="field-label">
          附注
        </view>
        <textarea
          v-model="draft.annotation"
          :maxlength="-1"
          class="field-textarea"
          auto-height
          placeholder="可使用 Markdown"
          :disabled="submitting"
        />
      </view>
      <view class="field">
        <view class="field-label">
          申请说明
        </view>
        <textarea
          v-model="reason"
          :maxlength="200"
          class="field-textarea"
          auto-height
          placeholder="说明修改原因、资料来源或需要协助核对的内容"
          :disabled="submitting"
        />
      </view>
      <view
        v-if="submitError"
        class="text-red margin-bottom"
      >
        {{ submitError }}
      </view>
      <button
        class="cu-btn bg-blue submit-button"
        :loading="submitting"
        :disabled="submitting"
        @tap="submit"
      >
        {{ submitting ? '正在提交…' : '提交申请（待审核）' }}
      </button>
      <view class="stand-view" />
    </view>
  </view>
</template>

<script>
import { checkWordApplications } from '@/services/capabilities';
import { createWordApplication, getWordDetails } from '@/services/word';
import { toLoginPage } from '@/routers/login';
import {
  buildWordApplicationPayload,
  createWordApplicationDraft,
  parseApplicationWordId,
} from '@/utils/wordApplication';

export default {
  data() {
    return {
      capabilityAllowed: false,
      id: 0,
      invalidId: false,
      draft: createWordApplicationDraft(),
      reason: '',
      authRequired: false,
      loading: false,
      loaded: false,
      loadError: '',
      submitting: false,
      submitted: false,
      applicationId: '',
      submitError: '',
    };
  },
  onLoad(options) {
    try {
      this.id = parseApplicationWordId(options.id);
      this.loadWord();
    } catch (error) {
      this.invalidId = true;
      this.loadError = error.message;
    }
  },
  onShow() {
    if (!this.invalidId) this.loadWord();
  },
  onHide() {
    this.capabilityAllowed = false;
  },
  methods: {
    toLoginPage,
    isLoggedIn() {
      return Boolean(uni.getStorageSync('token') && uni.getStorageSync('id'));
    },
    async loadWord() {
      if (this.loading || this.invalidId) return;
      this.authRequired = !this.isLoggedIn();
      if (this.authRequired) return;
      this.loading = true;
      this.loadError = '';
      this.capabilityAllowed = false;
      try {
        this.capabilityAllowed = await checkWordApplications();
        if (!this.capabilityAllowed || this.loaded) return;
        const source = this.id ? await getWordDetails(this.id) : {};
        this.draft = createWordApplicationDraft(source);
        this.loaded = true;
      } catch (error) {
        this.loadError = '加载词条失败，请检查网络后重试。';
      } finally {
        this.loading = false;
      }
    },
    async submit() {
      if (this.submitting || this.submitted || !this.loaded) return;
      if (!this.isLoggedIn()) {
        this.authRequired = true;
        return;
      }
      this.submitError = '';
      try {
        buildWordApplicationPayload(this.id, this.draft, this.reason);
      } catch (error) {
        this.submitError = error.message;
        return;
      }
      this.submitting = true;
      try {
        this.capabilityAllowed = await checkWordApplications();
        if (!this.capabilityAllowed) {
          this.submitError = '当前未开放词条申请，内容已保留。';
          return;
        }
        const result = await createWordApplication(this.id, this.draft, this.reason);
        this.applicationId = (result && result.id) || '';
        this.submitted = true;
      } catch (error) {
        this.submitError = (error && error.data && error.data.msg) || '提交失败，内容已保留，请稍后重试。';
      } finally {
        this.submitting = false;
      }
    },
    leave() {
      if (getCurrentPages().length > 1) {
        uni.navigateBack();
      } else {
        uni.redirectTo({ url: this.id ? `/pages/words/details?id=${this.id}` : '/pages/index' });
      }
    },
  },
};
</script>

<style scoped>
.word-application { padding-bottom: 40rpx; }
.notice { background: #edf5ff; color: #285275; border-radius: 12rpx; line-height: 1.7; }
.field { margin-bottom: 32rpx; }
.field-label { font-weight: bold; margin-bottom: 12rpx; }
.field-input, .field-textarea {
  box-sizing: border-box; background: #fff; padding: 22rpx; width: 100%;
  border: 1rpx solid #ddd; border-radius: 10rpx;
}
.field-input { height: 88rpx; }
.field-textarea { min-height: 120rpx; }
.submit-button { width: 100%; min-height: 88rpx; }
</style>
