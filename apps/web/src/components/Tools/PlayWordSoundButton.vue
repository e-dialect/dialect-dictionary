<template>
  <span class="word-audio">
    <a-button
      v-if="$featureEnabled('pinyin')"
      class="preview-button"
      :disabled="!pinyinSource && !lookupFailed"
      :icon="isActive(pinyinSource) ? 'stop' : 'sound'"
      size="small"
      type="link"
      :aria-pressed="isActive(pinyinSource)"
      @click="playSound(pinyinSource, '拼音')"
    >{{ buttonText(pinyinSource, '单字试听') }}</a-button>
    <a-button
      class="preview-button"
      :disabled="!ipaSource && !lookupFailed"
      :icon="isActive(ipaSource) ? 'stop' : 'sound'"
      size="small"
      type="link"
      :aria-pressed="isActive(ipaSource)"
      @click="playSound(ipaSource, 'IPA')"
    >{{ buttonText(ipaSource, $featureEnabled('pinyin') ? '连读试听' : '试听录音') }}</a-button>
  </span>
</template>

<script>
import axios from 'axios'
import { featureEnabled } from '@/config/site'
import { playAudio, stopAudio } from '@/utils/audio'

const validSource = value => typeof value === 'string' && value !== 'null' ? value : ''

export default {
  name: 'PlayWordSoundButton',
  props: {
    url: { type: String, default: '' },
    pinyin: { type: String, default: '' },
    ipa: { type: String, default: '' },
    wordId: { type: [String, Number], default: null }
  },
  data () {
    return {
      pinyin_url: '',
      ipa_url: '',
      fallback_url: '',
      fallback_position: '',
      lookupPending: false,
      lookupFailed: false,
      requestVersion: 0,
      audioState: { status: 'idle', src: '' }
    }
  },
  computed: {
    ipaSource () {
      return validSource(this.url) || this.ipa_url || this.fallback_url
    },
    pinyinSource () {
      return this.pinyin_url
    }
  },
  created () {
    this.loadPronunciations()
  },
  beforeDestroy () {
    this.requestVersion += 1
    stopAudio(this)
  },
  watch: {
    pinyin: 'loadPronunciations',
    ipa: 'loadPronunciations',
    wordId: 'loadPronunciations',
    url: 'loadPronunciations'
  },
  methods: {
    isActive (src) {
      return Boolean(src) && this.audioState.src === src && ['loading', 'playing'].includes(this.audioState.status)
    },
    buttonText (src, label) {
      if (this.isActive(src)) return this.audioState.status === 'loading' ? '加载中 · 停止' : '停止播放'
      if (src && this.audioState.src === src && this.audioState.status === 'error') return '重试播放'
      if (src) return label
      if (this.lookupPending) return '正在查找录音…'
      if (this.lookupFailed) return '重试查找录音'
      return '暂无录音'
    },
    async loadPronunciations () {
      const version = ++this.requestVersion
      stopAudio(this)
      this.audioState = { status: 'idle', src: '' }
      this.pinyin_url = ''
      this.ipa_url = ''
      this.fallback_url = ''
      this.fallback_position = ''
      this.lookupFailed = false
      this.lookupPending = true
      const combine = async params => {
        try {
          const response = await axios.get('pronunciation/combine', { params })
          return validSource(response.data.url)
        } catch {
          if (version === this.requestVersion) this.lookupFailed = true
          return ''
        }
      }
      const [ipa, pinyin] = await Promise.all([
        featureEnabled('pinyin') && this.ipa ? combine({ ipas: this.ipa }) : '',
        featureEnabled('pinyin') && this.pinyin ? combine({ pinyins: this.pinyin }) : ''
      ])
      if (version !== this.requestVersion) return
      this.ipa_url = ipa
      this.pinyin_url = pinyin
      if (!this.ipaSource && this.wordId) {
        try {
          const response = await axios.get('/pronunciation', { params: { word: this.wordId } })
          if (version !== this.requestVersion) return
          const record = (response.data.pronunciation || []).find(item => validSource(item.pronunciation?.source))
          if (record) {
            this.fallback_url = record.pronunciation.source
            this.fallback_position = [record.pronunciation.county, record.pronunciation.town].filter(Boolean).join(' ')
          }
        } catch {
          if (version === this.requestVersion) this.lookupFailed = true
        }
      }
      if (version === this.requestVersion) this.lookupPending = false
    },
    playSound (url, type) {
      if (!url) {
        if (this.lookupFailed) this.loadPronunciations()
        return
      }
      if (!this.isActive(url) && featureEnabled('geography') && type === 'IPA' && url === this.fallback_url && this.fallback_position) {
        this.$message.info(`当前播放口音来自：${this.fallback_position}`)
      }
      playAudio(url, {
        owner: this,
        onState: state => { this.audioState = state },
        onError: () => this.$message.error('播放失败，请点击重试播放')
      })
    }
  }
}
</script>

<style scoped>
.word-audio {
  display: inline-flex;
  flex-wrap: wrap;
  vertical-align: middle;
}
.preview-button {
  min-height: 36px;
  height: auto;
  white-space: normal;
}
</style>
