<template>
  <div class="header">
    <a-row align="middle" justify="space-around" type="flex">
      <a-col :span="3">
        <router-link to="/Home">
          <img v-if="$site.logo" :alt="$site.name" :src="$site.logo" style="height:40px;max-width:120px;object-fit:contain">
          <span v-else>{{ $site.shortName }}</span>
        </router-link>
      </a-col>

      <a-col :span="9">
        <a-menu v-model="tab" mode="horizontal">
          <a-menu-item key="Home">
            <router-link :to="{name:'Home'}">主页</router-link>
          </a-menu-item>
          <a-menu-item v-if="$featureEnabled('pinyin')" key="Pinyin">
            <router-link :to="{name:'Pinyin'}">拼音</router-link>
          </a-menu-item>
          <a-menu-item v-if="$featureEnabled('pinyin')" key="Dictionary">
            <router-link :to="{name:'Dictionary'}">词典</router-link>
          </a-menu-item>
          <a-menu-item key="WordList">
            <router-link :to="{name:'WordList'}">词单</router-link>
          </a-menu-item>
          <a-menu-item key="Articles">
            <router-link :to="{name:'Articles'}">文章</router-link>
          </a-menu-item>
          <a-menu-item key="Tools">
            <router-link :to="{name:'Tools'}">工具</router-link>
          </a-menu-item>
          <a-menu-item key="Rewards">
            <router-link :to="{name:'Rewards'}">积分</router-link>
          </a-menu-item>
        </a-menu>
      </a-col>

      <a-col :span="6">
        <a-input-search
          v-model="searchContent"
          placeholder="开始搜索"
          @search="search(searchContent)"
        />
      </a-col>

      <a-col :span="2">
        <header-user/>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import headerUser from './HeaderUser.vue'

export default {
  name: 'Header',
  components: {
    headerUser
  },
  data () {
    return {
      searchContent: ''
    }
  },
  computed: {
    tab: {
      get () {
        return this.$store.getters.tab
      },
      set (value) {
        this.$store.commit('tab', value)
      }
    }
  },
  methods: {
    search (content) {
      if (content) {
        if (!(this.$route.name === 'Search' && content === this.$route.query.key)) {
          this.$router.push({
            name: 'Search',
            query: { key: content }
          })
        }
      } else {
        this.$message.warning('请先输入搜索内容哦~')
      }
    }
  }
}
</script>

<style scoped>

</style>
