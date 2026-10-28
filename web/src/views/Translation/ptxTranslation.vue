<template>
  <a-card>
    <a-alert type="info" show-icon message="本部署包不提供普通话语音识别，请输入文字查询。"/>
    <a-input v-model="words" placeholder="输入要查询的文字" aria-label="查询文字" style="margin: 16px 0"/>
    <a-button icon="search" @click="search">搜索词典</a-button>
    <a-button v-if="$site.features.pinyin" icon="sound" :loading="loading" @click="lookupPronunciation">
      查询方言读音
    </a-button>
    <audio v-if="audioUrl" :src="audioUrl" controls style="display: block; margin-top: 16px"/>
    <PinyinList v-if="$site.features.pinyin && queriedWords" :key-words="queriedWords"/>
  </a-card>
</template>

<script>
import PinyinList from '../../components/Tools/PinyinList'

export default {
  name: 'TextPronunciationLookup',
  components: { PinyinList },
  data () {
    return { words: '', queriedWords: '', audioUrl: '', loading: false }
  },
  methods: {
    search () {
      const words = this.words.trim()
      if (words) this.$router.push({ name: 'Search', query: { key: words } })
      else this.$message.warning('请输入查询文字')
    },
    async lookupPronunciation () {
      if (!this.$site.features.pinyin || this.loading) return
      const words = this.words.trim()
      if (!words) {
        this.$message.warning('请输入查询文字')
        return
      }
      this.loading = true
      this.audioUrl = ''
      this.queriedWords = words
      try {
        const response = await this.$axios.get('pronunciation/combine', { params: { words } })
        this.audioUrl = response.data.url || ''
        if (this.audioUrl) this.$message.info('合成读音仅供参考，请核对方言资料')
      } catch (error) {
        this.$message.warning('此部署暂不能合成该段文字的读音')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
