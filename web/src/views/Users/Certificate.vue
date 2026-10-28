<script>
import { drawLearningRecord, learningRecordFields, RECORD_NOTICE } from '@/utils/certificateCanvas'

export default {
  name: 'Certificate',
  props: ['id'],
  data () {
    return {
      cert: {},
      loading: true,
      ready: false,
      error: '',
      actionError: '',
      requestNumber: 0,
      notice: RECORD_NOTICE
    }
  },
  computed: {
    recordFields () {
      return learningRecordFields(this.cert)
    }
  },
  watch: {
    id () {
      this.fetchCertificate()
    }
  },
  methods: {
    downloadCertificate () {
      if (!this.ready) return
      this.actionError = ''
      try {
        const a = document.createElement('a')
        a.href = this.$refs.certificate.toDataURL('image/png')
        a.download = 'learning-record.png'
        document.body.appendChild(a)
        a.click()
        a.remove()
      } catch (_) {
        this.actionError = '下载失败，请重试。'
      }
    },
    printCertificate () {
      if (!this.ready) return
      this.actionError = ''
      const printWindow = window.open('', '_blank')
      if (!printWindow) {
        this.actionError = '打印窗口未能打开，请允许弹出窗口后重试。'
        return
      }
      try {
        const doc = printWindow.document
        doc.title = '学习记录'
        const style = doc.createElement('style')
        style.textContent = 'body { margin: 0; } img { display: block; width: 100%; height: auto; } @page { margin: 12mm; }'
        doc.head.appendChild(style)
        const image = doc.createElement('img')
        image.alt = '学习记录；' + RECORD_NOTICE
        image.onload = () => {
          printWindow.onafterprint = () => printWindow.close()
          printWindow.focus()
          printWindow.print()
        }
        image.onerror = () => {
          this.actionError = '打印图片加载失败，请重试。'
          printWindow.close()
        }
        doc.body.appendChild(image)
        image.src = this.$refs.certificate.toDataURL('image/png')
      } catch (_) {
        this.actionError = '打印失败，请重试。'
        printWindow.close()
      }
    },
    async fetchCertificate () {
      const requestNumber = ++this.requestNumber
      this.loading = true
      this.ready = false
      this.error = ''
      this.actionError = ''
      try {
        const res = await this.$axios.get(`/certs/${encodeURIComponent(this.id)}`)
        if (requestNumber !== this.requestNumber) return
        if (!res.data.cert || typeof res.data.cert !== 'object' || Array.isArray(res.data.cert)) {
          throw new Error('Invalid learning record')
        }
        this.cert = res.data.cert
        await this.$nextTick()
        if (requestNumber !== this.requestNumber) return
        drawLearningRecord(this.$refs.certificate, this.cert)
        this.ready = true
      } catch (err) {
        if (requestNumber !== this.requestNumber) return
        this.error = err.response && err.response.status === 404
          ? '未找到该学习记录。'
          : '学习记录加载失败，请重试。'
      } finally {
        if (requestNumber === this.requestNumber) this.loading = false
      }
    }
  },
  mounted () {
    this.fetchCertificate()
  },
  beforeDestroy () {
    this.requestNumber++
  }
}
</script>

<template>
  <section class="learning-record">
    <h1>学习记录查询结果</h1>
    <p>{{ notice }}</p>
    <p v-if="loading" role="status">正在加载学习记录…</p>
    <p v-if="error" role="alert">{{ error }} <a-button @click="fetchCertificate">重试</a-button></p>
    <canvas ref="certificate" v-show="ready" role="img" aria-label="学习记录，详细文字见下方"/>
    <details v-if="ready">
      <summary>查看记录文字</summary>
      <dl>
        <template v-for="(field, index) in recordFields">
          <dt :key="'label-' + index">{{ field[0] }}</dt>
          <dd :key="'value-' + index">{{ field[1] }}</dd>
        </template>
      </dl>
    </details>
    <div v-if="ready" class="actions">
      <a-button-group>
        <a-button @click="downloadCertificate" type="primary" size="large">下载学习记录</a-button>
        <a-button @click="printCertificate" size="large">打印</a-button>
      </a-button-group>
    </div>
    <p v-if="actionError" role="alert">{{ actionError }}</p>
  </section>
</template>

<style scoped>
.learning-record { max-width: 900px; margin: 24px auto; padding: 0 16px; text-align: center; }
h1 { color: #203e50; }
canvas { display: block; width: 100%; height: auto; border: 1px solid #dae2e7; }
.actions { margin-top: 20px; }
details { margin-top: 12px; text-align: left; }
dt { font-weight: bold; }
dd { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
