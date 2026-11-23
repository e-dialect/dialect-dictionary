<template>
  <div v-if="$featureEnabled('pinyin')">
    <a-spin
      :delay="500"
      :spinning="loading">
      <a-collapse
        v-if="characters.length"
        :activeKey="Array.from(characters.keys())"
        :bordered="false"
        style="font-size: 22px;padding: 10px;background-color: white"
      >
        <a-collapse-panel
          v-for="(item,index) in characters "
          :key="index.toString()"
          :header="item.label===item.traditional?`${item.label}`:`${item.label}（${item.traditional}）`"
        >
          <div v-for="(jtem,index2) in item.characters" :key="index2.toString()">
            <a-breadcrumb>
              <a-breadcrumb-item>{{ jtem.county }}</a-breadcrumb-item>
              <a-breadcrumb-item>{{ jtem.town }}</a-breadcrumb-item>
            </a-breadcrumb>
            <span v-for="(ktem,index3) in jtem.characters" :key="index3.toString()" style="padding-right: 16px">
              <span v-if="ktem.word===null">{{ ktem.pinyin }}</span>
              <router-link v-else :to="{name:'WordDetails',params:{id:ktem.word}}">{{ ktem.pinyin }}</router-link>
              <PlaySoundButton :url="ktem.source" :pinyin="ktem.pinyin" :word-id="ktem.word"/>
            </span>
          </div>
        </a-collapse-panel>
      </a-collapse>
      <a-button v-else-if="failed" @click="getPinyin(keyWords)">字音加载失败，重试</a-button>
      <a-empty v-else-if="!loading" description="暂无字音"/>
    </a-spin>
  </div>
</template>

<script>
import axios from 'axios'
import PlaySoundButton from './PlaySoundButton'

export default {
  name: 'PinyinList',
  components: { PlaySoundButton },
  props: ['keyWords'],
  data () {
    return {
      loading: false,
      failed: false,
      requestId: 0,
      characters: []
    }
  },
  watch: {
    keyWords: {
      immediate: true,
      handler (key) { this.getPinyin(key) }
    }
  },
  methods: {
    async getPinyin (key) {
      const request = ++this.requestId
      this.characters = []
      this.failed = false
      this.loading = Boolean(key && this.$featureEnabled('pinyin'))
      if (!this.loading) return
      try {
        const { data } = await axios.get('/characters/words/v2', { params: { search: key } })
        if (request === this.requestId) this.characters = data.characters
      } catch {
        if (request === this.requestId) this.failed = true
      } finally {
        if (request === this.requestId) this.loading = false
      }
    }
  }
}
</script>
