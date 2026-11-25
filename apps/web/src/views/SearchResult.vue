<template>
  <div class="search-results">
    <a-card>
      <template slot="title">
        <a-input-search
          ref="searchInput"
          v-model="searchContent"
          enter-button="搜索"
          aria-label="搜索词语或文章"
          placeholder="输入词语、普通话释义或文章关键词"
          size="large"
          @search="search(searchContent)"
        />
      </template>
      <p v-if="!keyWords">请输入要查询的内容。</p>
      <template v-else>
        <h1 class="search-heading">“{{ keyWords }}”的搜索结果</h1>
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
        <h2>词语 <span v-if="!loading.words && !failed.words" class="result-count">{{ words.length }} 条</span></h2>
        <p v-if="!loading.words && !failed.words && words.length >= 200" class="result-hint">当前显示前 200 条相关词语，缩小关键词可以更快找到目标。</p>
        <a-row justify="space-around" type="flex">
          <span v-if="loading.words" role="status">正在查询词语…</span>
          <a-button v-else-if="failed.words" @click="loadResults('words', requestId)">词语加载失败，重试</a-button>
          <div v-else-if="!words.length" class="result-empty" role="status">
            <p>未找到相关词语</p>
            <p>试试缩短关键词，或换用普通话释义。未搜到不代表这个词不存在。</p>
            <a-button @click="$refs.searchInput.focus()">修改关键词</a-button>
          </div>
          <WordList v-else
            :list-data="words"
            :page-size="8"
            :page="wordsPage"
            class="result-list"
            @page-change="changePage('words', $event)"
          />
        </a-row>
        <a-divider></a-divider>
        <h2>文章 <span v-if="!loading.articles && !failed.articles" class="result-count">{{ articles.length }} 篇</span></h2>
        <a-row justify="space-around" type="flex">
          <span v-if="loading.articles" role="status">正在查询文章…</span>
          <a-button v-else-if="failed.articles" @click="loadResults('articles', requestId)">文章加载失败，重试</a-button>
          <div v-else-if="!articles.length" class="result-empty" role="status">
            <p>未找到相关文章</p>
            <p>可以换用文章标题中的关键词继续搜索。</p>
          </div>
          <ArticleList v-else
            :list-data="articles"
            :page-size="8"
            :page="articlesPage"
            class="result-list"
            @page-change="changePage('articles', $event)"/>
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
import { resultPage } from '@/utils/resultPage'

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
    },
    wordsPage () {
      return resultPage(this.$route.query.wordsPage, this.words.length, 8)
    },
    articlesPage () {
      return resultPage(this.$route.query.articlesPage, this.articles.length, 8)
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
    changePage (resource, page) {
      const query = { ...this.$route.query }
      const key = resource + 'Page'
      if (page > 1) query[key] = String(page)
      else delete query[key]
      if (query[key] === this.$route.query[key]) return
      // Replace the search entry so returning from a detail opens this page.
      this.$router.replace({ name: 'Search', query })
    },
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
.search-results { width: 100%; padding-bottom: 24px; }
.search-heading { font-size: 22px; overflow-wrap: anywhere; }
.result-count { margin-left: 8px; color: #595959; font-size: 14px; font-weight: normal; }
.result-hint { color: #595959; }
.result-list { width: 100%; }
.result-empty { width: 100%; padding: 24px; background: #fafafa; border: 1px solid #e8e8e8; border-radius: 6px; color: #595959; }
.result-empty p:first-child { color: #262626; font-size: 16px; }
</style>
