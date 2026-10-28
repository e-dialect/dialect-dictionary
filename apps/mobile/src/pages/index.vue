<template>
  <view>
    <basics v-if="currentPage==='basics'" />
    <tools v-if="currentPage==='tools'" />
    <InteractionPage v-if="currentPage==='InteractionPage'" />
    <me v-if="currentPage==='me'" />

    <view
      class="cu-bar tabbar bg-white shadow foot"
      style="border-radius: 50rem"
    >
      <view
        v-for="item in tabBar"
        :key="item.name"
        class="action"
        :class="{ 'text-blue': currentPage === item.name }"
        data-cur="basics"
        @tap="changePage(item.name)"
      >
        <view :class="['text-xl', 'cuIcon-' + item.icon]" />
        <text>{{ item.label }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import siteConfig from '@/config/site';
import { defaultMessage } from '@/services/shareMessages';
import { toLoginPage } from '@/routers/login';
import basics from './home.vue';
import tools from './tools/index.vue';
import InteractionPage from './articles/index.vue';
import me from './users/me.vue';

export default {
  components: {
    basics,
    tools,
    InteractionPage,
    me,
  },
  data() {
    return {
      currentPage: 'basics',
      tabBar: [
        {
          name: 'basics',
          icon: 'home',
          label: '首页',
        },
        {
          name: 'tools',
          icon: 'settings',
          label: '工具',
        },
        {
          name: 'InteractionPage',
          icon: 'comment',
          label: '文章',
        },
        {
          name: 'me',
          icon: 'people',
          label: '我的',
        },
      ],
    };
  },
  onShareAppMessage() {
    return {
      title: siteConfig.name,
      path: '/pages/index',
      ...defaultMessage(),
    };
  },
  onLoad(options) {
    if (options.status) {
      this.currentPage = options.status;
    }
  },
  methods: {
    /**
     * 切换页面
     * @param page 新页面
     */
    async changePage(page) {
      if (page === 'me') {
        if (!uni.getStorageSync('token')) {
          uni.showToast({
            title: '请先登录!',
            icon: 'none',
          });
          setTimeout(() => {
            toLoginPage();
          }, 1000);
          return;
        }
      }
      this.currentPage = page;
    },
  },
};
</script>
<style></style>
