<template>
  <div>
  <a-menu v-model="tab1" mode="horizontal">
    <a-menu-item key="xtpTranslation">
      <router-link replace :to="{name:'xtpTranslation'}">
        {{ $site.dialect.name }}识别
      </router-link>
    </a-menu-item>
    <a-menu-item key="ptxTranslation">
      <router-link replace :to="{name:'ptxTranslation'}">
        文字查词与查音
      </router-link>
    </a-menu-item>
  </a-menu>
  </div>
</template>

<script>
export default {
  name: 'translationHeader',
  computed: {
    tab1: {
      get () {
        return this.$store.getters.tab1
      },
      set (value) {
        this.$store.commit('tab1', value)
      }
    }
  }
}
</script>

<style scoped>

</style>
