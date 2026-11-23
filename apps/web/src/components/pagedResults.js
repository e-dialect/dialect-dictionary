import axios from 'axios'

// Both result lists receive ordered IDs and fetch the rows for the visible page.
export default function pagedResults (resource) {
  return {
    props: { listData: Array, pageSize: Number },
    data () {
      return { listSource: [], loading: false, failed: false, currentPage: 1, requestId: 0 }
    },
    computed: {
      pagination () {
        return {
          current: this.currentPage,
          pageSize: this.pageSize,
          total: (this.listData || []).length,
          showQuickJumper: resource === 'words',
          onChange: this.getCurrentPageData
        }
      }
    },
    watch: {
      listData: {
        immediate: true,
        handler () { this.getCurrentPageData(1) }
      }
    },
    methods: {
      async getCurrentPageData (page) {
        const request = ++this.requestId
        const ids = (this.listData || []).slice((page - 1) * this.pageSize, page * this.pageSize)
        this.currentPage = page
        this.listSource = []
        this.failed = false
        this.loading = ids.length > 0
        if (!ids.length) return
        try {
          const { data } = await axios.put('/' + resource, { [resource]: ids })
          if (request === this.requestId) this.listSource = data[resource]
        } catch {
          if (request === this.requestId) this.failed = true
        } finally {
          if (request === this.requestId) this.loading = false
        }
      }
    }
  }
}
