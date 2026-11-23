<template>
  <a-spin :delay="500" :spinning="spinning">
    <a-card>
      <template v-slot:title>
        <h1 v-if="id">词条编辑</h1>
        <h1 v-else>词条创建</h1>
      </template>

      <p v-if="notice" role="status">{{ notice }}</p>
      <a-button v-if="!ready && !spinning" @click="openForm">重新检查</a-button>
      <template v-if="ready">
        <a-form-model :labelCol="{span: 3}" :model="word" :wrapperCol="{span:16,offset:1}">
          <a-form-model-item label="词条">
            <a-input v-model="word.word" placeholder="填入词条标题"/>
          </a-form-model-item>
          <a-form-model-item label="拼音">
            <a-input v-model="word.standard_pinyin" placeholder="词条的拼音写法（不用类化）"/>
          </a-form-model-item>
          <a-form-model-item label="IPA">
            <a-input v-model="word.standard_ipa" placeholder="词条的IPA（实际发音），实在不会可以留空找管理员帮忙"/>
          </a-form-model-item>
          <a-form-model-item label="标签">
            <LineTags v-model="word.tags" tips="词条标签"/>
          </a-form-model-item>
          <a-form-model-item label="释义">
            <DefinitionEdit v-model="word.definition"/>
          </a-form-model-item>
          <a-form-model-item label="普通话词汇">
            <LineTags v-model="word.mandarin" tips="新词汇"></LineTags>
          </a-form-model-item>
          <a-form-model-item label="相关词条">
            <SelectWord :default-value="related_words" v-model="word.related_words"/>
          </a-form-model-item>
          <a-form-model-item label="相关文章">
            <SelectArticle v-model="word.related_articles" :default-value="related_articles"/>
          </a-form-model-item>
          <a-form-model-item label="附注">
            <MarkdownEditor v-model="word.annotation"></MarkdownEditor>
          </a-form-model-item>
          <a-form-model-item label="理由说明">
            <a-input v-if="id" v-model="reason" placeholder="[可选]说明更改了哪些点，为何修改有助于更好帮助管理员审核"/>
            <a-input v-else v-model="reason" placeholder="[可选]说明有哪些看可能把握不准的地方，有助于更好帮助管理员审核"/>
          </a-form-model-item>
        </a-form-model>
        <a-button :loading="submitting" :disabled="submitted" @click="submit">
          {{ id ? '提交更改' : '创建词条' }}
        </a-button>
      </template>
    </a-card>
  </a-spin>
</template>

<script>
import { checkWordApplications } from '@/services/capabilities'
import DefinitionEdit from '../../components/Word/DefinitionEdit'
import axios from 'axios'
import MarkdownEditor from '../../components/Articles/MarkdownEditor'
import LineTags from '../../components/Word/LineTags'
import SelectWord from '../../components/Word/SelectWord'
import SelectArticle from '../../components/Word/SelectArticle'

function emptyWord () {
  return { word: '', definition: '', annotation: '', standard_pinyin: '', standard_ipa: '', tags: [], mandarin: [], related_words: [], related_articles: [] }
}

export default {
  name: 'WordEdit',
  components: {
    SelectArticle,
    SelectWord,
    LineTags,
    MarkdownEditor,
    DefinitionEdit
  },
  data () {
    return {
      spinning: true,
      ready: false,
      submitting: false,
      submitted: false,
      revision: 0,
      notice: '',
      word: emptyWord(),
      related_words: [],
      related_articles: [],
      reason: ''
    }
  },
  computed: {
    id () {
      if (this.$route.name === 'WordCreate') {
        return 0
      } else {
        return +this.$route.params.id
      }
    },
    content () {
      const content = emptyWord()
      for (const field of Object.keys(content)) content[field] = this.word[field]
      content.related_words = this.word.related_words.map(item => item.id || item.key)
      content.related_articles = this.word.related_articles.map(item => item.id || item.key)
      return content
    }
  },
  created () {
    this.openForm()
  },
  beforeDestroy () {
    this.revision++
  },
  watch: {
    $route () {
      this.getWordDetails()
    }
  },
  methods: {
    async openForm () {
      const revision = ++this.revision
      this.ready = false
      this.submitted = false
      this.submitting = false
      this.spinning = true
      this.notice = '正在检查词条申请状态…'
      try {
        const enabled = await checkWordApplications()
        if (revision !== this.revision) return
        if (!enabled) {
          this.notice = '本站当前未开放词条申请。'
          return
        }
        if (!this.$store.getters.loginStatus && !localStorage.getItem('token')) {
          this.$router.push({ name: 'Login' })
          return
        }
        const word = this.id ? (await axios.get('/words/' + this.id)).data.word : emptyWord()
        if (revision !== this.revision) return
        this.word = word
        this.related_articles = word.related_articles
        this.related_words = word.related_words
        this.reason = ''
        this.notice = ''
        this.ready = true
      } catch {
        if (revision === this.revision) this.notice = '暂时无法打开词条申请，请重新检查。'
      } finally {
        if (revision === this.revision) this.spinning = false
      }
    },
    async submit () {
      if (!this.ready || this.submitting || this.submitted) return
      const revision = this.revision
      let sending = false
      this.submitting = true
      this.notice = ''
      try {
        const enabled = await checkWordApplications()
        if (revision !== this.revision) return
        if (!enabled) {
          this.notice = '本站当前未开放词条申请，已保留填写内容。'
          return
        }
        sending = true
        const { data } = await axios.post('/words/applications', {
          content: this.content, word: this.id, reason: this.reason
        })
        if (revision !== this.revision) return
        this.submitted = true
        this.$message.success('申请编号 ' + data.id + '，已提交，等待管理员审核。')
        this.$router.push(this.id ? { name: 'WordDetails', params: { id: this.id } } : { name: 'Home' })
      } catch (error) {
        if (revision !== this.revision) return
        if (!sending) {
          this.notice = '暂时无法检查本站申请状态，本次尚未提交。已保留填写内容。'
          return
        }
        const status = error.response?.status
        this.notice = status === 401 || status === 403
          ? '账号当前无法提交，请核对登录状态和贡献权限。已保留填写内容。'
          : '暂时无法确认提交结果，已保留填写内容。'
      } finally {
        if (revision === this.revision) this.submitting = false
      }
    }
  }
}
</script>
