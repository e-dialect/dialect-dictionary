<template>
  <a-card>
    <div v-for="(item,index) in tools.filter(tool => routeEnabled(tool.routerName))" :key="index">
      <a-card-grid hoverable style="width:33%;text-align:center">
        <a-card
          :bordered="false"
          @click="onCardClick(item)"
        >
          <template v-slot:cover>
            <div style="padding: 24px 12px; font-size: 20px">{{ item.label }}</div>
          </template>
        </a-card>

      </a-card-grid>
    </div>
  </a-card>
</template>

<script>
import { routeEnabled } from '@/config/features'
export default {
  name: 'Tools',
  data () {
    return {

      tools: [
        {
          label: '条件查字',
          routerName: 'Conditions',
          alt: '拼音查字：根据声母、韵母、声调筛选符合条件的单字',
          disabled: false
        },
        {
          label: '拼音速查',
          routerName: 'Characters',
          alt: '拼音速查：快速查询一串汉字对应的所有拼音',
          disabled: false
        },
        {
          label: '聪明花开',
          routerName: 'PuxianExam',
          alt: '聪明花开：方言与地方文化小测试',
          disabled: false
        },
        {
          label: '快速录制',
          routerName: 'QuickRecording',
          alt: '快速录制：大批量快速录制方言语音',
          disabled: false
        },
        {
          label: '录音审核',
          routerName: 'RecordConfirming',
          alt: '录音审核：（管理员）界面友好地审查录音情况',
          disabled: false
        },
        {
          label: '词条审核',
          alt: '词条审核：（管理员）界面友好地审查词条情况',
          routerName: 'WordConfirming',
          disabled: false
        },
        {
          label: '方言曲库',
          routerName: 'Music',
          alt: '方言曲库：用方言一样能创作出好听的歌曲',
          disabled: false
        },
        {
          label: '亲戚计算',
          routerName: 'Relative',
          alt: '亲戚计算：计算两个人的亲戚关系',
          disabled: false
        },
        {
          label: '日常用语',
          alt: '日常用语：英语、普通话、方言正字与拼音共同对照',
          routerName: 'DailyExpressions',
          disabled: false
        },
        {
          label: '语音识别',
          alt: '方言语音识别需独立配置服务；普通话入口提供文字查词与查音',
          routerName: 'xtpTranslation',
          disabled: false
        },
        {
          label: '排行榜单',
          alt: '用户贡献情况排名',
          routerName: 'RankList',
          disabled: false
        },
        {
          label: '敬请期待',
          alt: '更多功能正在开发中',
          routerName: 'tools',
          disabled: true
        }
      ]
    }
  },
  methods: {
    routeEnabled,
    onCardClick (item) {
      if (!item.disabled) {
        this.$router.push({ name: item.routerName })
      } else {
        this.$message.warning('功能正在开发中，请耐心等候')
      }
    }
  }
}
</script>

<style scoped>

</style>
