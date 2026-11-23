<template>
  <div>
    <a-button v-if="failed" @click="getCurrentPageData(currentPage)">加载失败，重试本页</a-button>
    <a-list
      :data-source="listSource || []"
      :loading="{spinning: loading, delay: 500}"
      :pagination="pagination"
      item-layout="vertical"
    >
      <template v-slot:renderItem="item">
        <a-list-item>
          <template v-slot:extra>
            <img
              :src="item.article.cover"
              alt="文章封面"
              width="300"
            />
          </template>
          <a-list-item-meta :description="item.article.description">
            <template v-slot:title>
              <h2>
                <router-link :to="{name:'ArticleDetails',params:{id:item.article.id.toString()}}">
                  {{ item.article.title }}
                </router-link>
              </h2>
            </template>
          </a-list-item-meta>
        </a-list-item>
      </template>
    </a-list>
  </div>
</template>
<script>
import pagedResults from '@/components/pagedResults'

export default {
  name: 'ArticleList',
  mixins: [pagedResults('articles')]
}
</script>
<style></style>
