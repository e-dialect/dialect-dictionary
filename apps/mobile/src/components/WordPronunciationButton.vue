<template>
  <button
    class="pronunciation-button"
    :disabled="isDisabled"
    :aria-label="buttonText"
    :aria-pressed="isActive"
    @tap.stop="play"
  >
    <text :class="isActive ? 'cuIcon-stop' : 'cuIcon-notificationfill'" />
    {{ buttonText }}
  </button>
</template>

<script>
import { featureEnabled } from '@/config/site';
import { playAudio, stopAudio, audioGeneration } from '@/utils/audio';
import { combinePronunciationByIpa, combinePronunciationByPinyin, getPronunciations } from '@/services/pronunciation';

const validSource = (value) => (typeof value === 'string' && value !== 'null' ? value : '');

export default {
  name: 'WordPronunciationButton',
  props: {
    source: { type: String, default: '' },
    pinyin: { type: String, default: '' },
    ipa: { type: String, default: '' },
    wordId: { type: [Number, String], default: null },
  },
  data() {
    return {
      url: '',
      accept: false,
      firstPronunciation: null,
      lookupPending: false,
      lookupFailed: false,
      synthesizing: false,
      modalOpen: false,
      requestVersion: 0,
      audioState: { status: 'idle', src: '' },
    };
  },
  computed: {
    isDisabled() {
      return this.lookupPending
        || (!this.recordingSource && !this.canSynthesize && !this.lookupFailed);
    },
    recordingSource() {
      return validSource(this.source)
        || validSource(this.firstPronunciation?.pronunciation?.source);
    },
    canSynthesize() {
      return featureEnabled('pinyin') && Boolean(this.ipa || this.pinyin);
    },
    isActive() {
      return ['loading', 'playing'].includes(this.audioState.status);
    },
    buttonText() {
      if (this.lookupPending) return '查找录音中…';
      if (this.synthesizing) return '合成中 · 取消';
      if (this.isActive) return this.audioState.status === 'loading' ? '加载中 · 停止' : '停止播放';
      if (this.audioState.status === 'error') return '重试播放';
      if (this.recordingSource) return '试听录音';
      if (this.lookupFailed) return '重试查找录音';
      return this.canSynthesize ? '尝试合成' : '暂无录音';
    },
  },
  watch: {
    wordId: 'loadPronunciation',
    source: 'loadPronunciation',
    ipa: 'loadPronunciation',
    pinyin: 'loadPronunciation',
  },
  mounted() {
    this.loadPronunciation();
  },
  beforeUnmount() {
    this.requestVersion += 1;
    stopAudio(this);
  },
  methods: {
    async loadPronunciation() {
      this.requestVersion += 1;
      const version = this.requestVersion;
      stopAudio(this);
      this.audioState = { status: 'idle', src: '' };
      this.url = '';
      this.accept = false;
      this.firstPronunciation = null;
      this.lookupFailed = false;
      this.lookupPending = false;
      this.synthesizing = false;
      this.modalOpen = false;
      if (validSource(this.source) || !this.wordId) return;
      this.lookupPending = true;
      try {
        const recordings = await getPronunciations({ word: this.wordId, pageSize: 1, page: 1 });
        if (version !== this.requestVersion) return;
        this.firstPronunciation = recordings.find(
          (item) => validSource(item.pronunciation?.source),
        ) || null;
      } catch {
        if (version === this.requestVersion) this.lookupFailed = true;
      } finally {
        if (version === this.requestVersion) this.lookupPending = false;
      }
    },
    preview(src) {
      playAudio(src, true, {
        owner: this,
        onState: (state) => { this.audioState = state; },
      });
    },
    async play() {
      if (this.synthesizing) {
        this.requestVersion += 1;
        this.synthesizing = false;
        return;
      }
      if (this.isActive) {
        stopAudio(this);
        return;
      }
      if (this.lookupPending || this.modalOpen) return;
      if (this.recordingSource) {
        this.preview(this.recordingSource);
        return;
      }
      if (this.lookupFailed) {
        await this.loadPronunciation();
        return;
      }
      if (!this.canSynthesize) return;
      if (this.accept) {
        await this.playUrl();
        return;
      }
      const version = this.requestVersion;
      const generation = audioGeneration();
      this.modalOpen = true;
      uni.showModal({
        title: '暂无有效人声录音',
        content: '是否尝试播放合成语音？合成语音仅供参考，不保证其正确性！',
        confirmText: '继续',
        success: async (res) => {
          if (version !== this.requestVersion
            || generation !== audioGeneration() || !res.confirm) return;
          this.accept = true;
          await this.playUrl();
        },
        complete: () => {
          if (version === this.requestVersion) this.modalOpen = false;
        },
      });
    },
    async playUrl() {
      const version = this.requestVersion;
      // A new listening request supersedes both playback and pending synthesis.
      stopAudio();
      const generation = audioGeneration();
      this.synthesizing = true;
      try {
        let { url } = this;
        if (!url && this.ipa) url = validSource(await combinePronunciationByIpa(this.ipa));
        if (version !== this.requestVersion || generation !== audioGeneration()) return;
        if (!url && this.pinyin) url = validSource(await combinePronunciationByPinyin(this.pinyin));
        if (version !== this.requestVersion || generation !== audioGeneration()) return;
        this.url = url;
        if (url) this.preview(url);
        else uni.showToast({ title: '暂无可合成的语音，可稍后重试', icon: 'none' });
      } finally {
        if (version === this.requestVersion) this.synthesizing = false;
      }
    },
  },
};
</script>

<style scoped>
.pronunciation-button {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  min-height: 72rpx;
  margin: 8rpx 12rpx;
  padding: 8rpx 16rpx;
  color: #176aa8;
  background: #edf6ff;
  font-size: 26rpx;
  line-height: 1.4;
  vertical-align: middle;
}
.pronunciation-button[disabled] {
  color: #6b7280;
  background: #f1f3f5;
}
</style>
