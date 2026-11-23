<template>
  <div style="width: 90%">
    <a-card>
      <template slot="title">
        <a-input-search
          v-model="searchContent"
          enter-button
          placeholder="请输入搜索内容"
          size="large"
          @search="search(searchContent)"
        />
      </template>
      <p v-if="!keyWords">请输入要查询的内容。</p>
      <template v-else>
        <div v-if="$featureEnabled('pinyin') && Chinese.length">
          <h1>听句子</h1>
          <a-button icon="sound" @click="playWords()" style="margin-left:100px">
            我已保护好耳朵，坚持试听一下
          </a-button>
          <a-divider></a-divider>
        </div>
        <div v-if="$featureEnabled('pinyin') && Chinese.length">
          <h1>查单字</h1>
          <a-row justify="space-around" type="flex">
            <PinyinList
              :key="keyWords"
              :key-words="Chinese"
              style="width: 80%"
            />
          </a-row>
          <a-divider></a-divider>
        </div>
        <h1>查词语</h1>
        <a-row justify="space-around" type="flex">
          <span v-if="loading.words" role="status">正在查询词语…</span>
          <a-button v-else-if="failed.words" @click="loadResults('words', requestId)">词语加载失败，重试</a-button>
          <WordList v-else
            :list-data="words"
            :page-size="8"
            style="width: 80%"
          />
        </a-row>
        <a-divider></a-divider>
        <h1>查文章</h1>
        <a-row justify="space-around" type="flex">
          <span v-if="loading.articles" role="status">正在查询文章…</span>
          <a-button v-else-if="failed.articles" @click="loadResults('articles', requestId)">文章加载失败，重试</a-button>
          <ArticleList v-else
            :list-data="articles"
            :page-size="8"
            style="width: 80%"/>
        </a-row>
      </template>
    </a-card>
  </div>
</template>

<script>
import PinyinList from '../components/Tools/PinyinList'
import WordList from '../components/Tools/WordList'
import ArticleList from '../components/Articles/ArticleList'
import axios from 'axios'

export default {
  name: 'SearchResult',
  components: {
    ArticleList,
    WordList,
    PinyinList
  },
  props: [
    'keyWords'
  ],
  computed: {
    Chinese () {
      return (this.keyWords || '').replaceAll(/[^\u4e00-\u9fa5]/ig, '')
    }
  },
  data () {
    return {
      requestId: 0,
      failed: { words: false, articles: false },
      loading: {
        articles: false,
        words: false
      },
      articles: [],
      words: [],
      searchContent: '',
      pronunciation: {
        url: '',
        loading: false,
        disabled: false
      }
    }
  },
  created () {
    this.loadingData()
  },

  watch: {
    keyWords () {
      this.loadingData()
    }
  },
  methods: {
    async loadResults (resource, request) {
      this.loading[resource] = true
      this.failed[resource] = false
      try {
        const { data } = await axios.get('/' + resource, { params: { search: this.keyWords } })
        if (request === this.requestId) this[resource] = data[resource]
      } catch {
        if (request === this.requestId) this.failed[resource] = true
      } finally {
        if (request === this.requestId) this.loading[resource] = false
      }
    },
    async loadingData () {
      const request = ++this.requestId
      this.searchContent = this.keyWords || ''
      this.words = []
      this.articles = []
      this.loading = { articles: false, words: false }
      this.failed = { articles: false, words: false }
      this.pronunciation = { url: '', loading: false, disabled: true }
      if (!this.searchContent) return
      this.loadResults('words', request)
      this.loadResults('articles', request)
      if (!this.Chinese || !this.$featureEnabled('pinyin')) return
      this.pronunciation.loading = true
      try {
        const { data } = await axios.get('/pronunciation/combine', { params: { words: this.Chinese } })
        if (request === this.requestId) this.pronunciation = { url: data.url, loading: false, disabled: !data.url }
      } catch {
        if (request === this.requestId) this.pronunciation.loading = false
      }
    },
    search (content) {
      content = content.trim()
      if (content) {
        if (content !== this.keyWords) {
          this.$router.push({
            name: 'Search',
            query: { key: content }
          })
        }
      } else {
        this.$message.warning('请先输入搜索内容哦~')
      }
    },
    playWords () {
      if (!this.$featureEnabled('pinyin')) return
      if (this.pronunciation.loading) {
        this.$message.warning('正在合成中，请稍后再试！')
        return
      }
      if (this.pronunciation.disabled) {
        this.$message.warning('很抱歉，这句话太难了，暂时合成不了！')
        return
      }
      this.$message.warning('该语音由机器生成仅供参考！（可能存在错误）')
      new Audio(this.pronunciation.url).play()
    }
  }
}
</script>

<style scoped>

</style>
