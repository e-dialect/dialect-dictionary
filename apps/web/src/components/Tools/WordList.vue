<template>
  <div>
    <a-button v-if="failed" @click="getCurrentPageData(currentPage)">加载失败，重试本页</a-button>
    <a-list
    :data-source="listSource || []"
    :loading="{spinning: loading, delay: 500}"
    :pagination="pagination"
  >
    <template v-slot:renderItem="item">
      <a-card
        :hoverable="true"
        style="width: 100%;"
      >
        <a-card-meta :description="item.word.definition.slice(0,100)">
          <template v-slot:title>
            <span style="font-size: 150%">
               <router-link
                 :to="{name:'WordDetails',params:{id:item.word.id.toString()}}"
                 style="color:black"
               >
                 {{ item.word.word }}
               </router-link>
            </span>
            <span style="font-size: 80%;padding-left: 10px">
                {{ item.word.standard_pinyin }}
              </span>
            <span style="font-size: 80%;color: rgb(155,155,155);padding-left: 10px">
                / {{ item.word.standard_ipa }}/
              </span>
            <word-tag :tags="item.word.tags" style="margin-left: 10px"/>
            <PlayWordSoundButton
              :url="item.pronunciation.url"
              :ipa="item.word.standard_ipa"
              :pinyin="item.word.standard_pinyin"
              :word-id="item.word.id"
            />
          </template>
        </a-card-meta>
        <div style="text-align: end">
          <a-button type="link">
            <router-link :to="{name:'WordDetails',params:{id:item.word.id.toString()}}">
              更多
              <a-icon type="double-right"/>
            </router-link>
          </a-button>
        </div>

      </a-card>
    </template>
  </a-list>
  </div>
</template>
<script>
import pagedResults from '@/components/pagedResults'
import PlayWordSoundButton from './PlayWordSoundButton'
import WordTag from '@/components/Word/WordTag.vue'

export default {
  name: 'WordList',
  components: { WordTag, PlayWordSoundButton },
  mixins: [pagedResults('words')]
}
</script>
