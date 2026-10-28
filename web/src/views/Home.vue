<template>
  <div class="body">
    <h1>{{ $site.name }}</h1>
    <a-alert type="info" :message="$site.contentSource.notice" show-icon />
    <p>{{ $site.dialect.name }} · 内容来源：{{ $site.contentSource.name }}</p>
    <a-row
      justify="center"
      style="padding: 12px 0;"
      type="flex"
    >
      <a-card hoverable style="text-align: center;">
        <img v-if="$site.logo" :alt="$site.name" :src="$site.logo" style="padding-top: 32px" width="40%">
        <a-input-search
          v-model="searchContent"
          placeholder="一键检索你想知道的"
          style="width:70%;"
          @search="search(searchContent)"
        />
        <div style="padding-top: 24px;text-align: left;font-size: 90%;margin:24px 24px;line-height: 8px;color: #8b8b8b">
          <p style="color: #414141">目前支持搜单字、搜词语、搜文章功能。</p>
          <p><span class="show-span">普通查询</span>查单字 搜词语 搜文章</p>
          <p v-if="$featureEnabled('quiz')"><span class="show-span">查询证书</span>输入开头为PLPT的证书编号</p>
          <p v-if="$featureEnabled('pinyin')"><span class="show-span">拼音查字典</span>pinyin:(你要搜的拼音)</p>
        </div>
      </a-card>
    </a-row>
    <a-row
      justify="space-around"
      style="padding: 10px 0 20px;"
      type="flex"
    >
      <a-col v-for="item in toolList.filter(tool => routeEnabled(tool.routerName))" :key="item.id" :span="21/toolList.length">
        <a-card hoverable>
          <template v-slot:cover>
            <a-button style="width: 100%; padding: 24px 8px; height: auto" @click="$router.push({name:item.routerName})">{{ item.label }}</a-button>
          </template>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import { routeEnabled } from '@/config/features'
export default {
  name: 'Home',
  data () {
    return {
      searchContent: '',
      toolList: [
        {
          id: 1,
          label: '音序查词',
          routerName: 'Dictionary',
          disabled: false
        },
        {
          id: 2,
          label: '快速录制',
          routerName: 'QuickRecording',
          disabled: false
        },
        {
          id: 3,
          label: '条件查字',
          routerName: 'Conditions',
          disabled: false
        }
      ]
    }
  },
  methods: {
    routeEnabled,
    search (content) {
      if (!content) {
        this.$message.warning('请先输入搜索内容哦~')
        return
      }
      if (this.$featureEnabled('quiz') && content.substring(0, 4) === 'PLPT') {
        this.$router.push({
          path: `/users/certificate/${content}`
        })
        return
      }
      if (this.$featureEnabled('pinyin') && content.substring(0, 6) === 'pinyin') {
        this.$router.push({
          path: '/tools/conditions?pinyin=' + content.substring(7)
        })
        return
      }
      this.$router.push({
        name: 'Search',
        query: { key: content }
      })
    }
  }
}
</script>
<style>
.select-word {
  background: #fff;
  position: fixed;
  margin-top: -70px;
  margin-left: -50px;
  line-height: 42px;
  border-radius: 5px;
  box-shadow: 0 0 5px #ccc;
}
li {
  padding: 0 15px;
  color: #8c8c8c;
  list-style: none;
}
li:hover {
  color: #417be0;
  cursor: pointer;
  background: #e7edfb;
}
.show-span{
  color: #414141;
  font-weight: bold;
  margin-right: 10px;
}
</style>
