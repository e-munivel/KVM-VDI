<template>
    <b-dropdown :text="'🌐 ' + langs[$i18n.locale]" size="sm" variant="outline-secondary">
        <b-dropdown-item v-for="(text, lang) in langs" :key="lang" href="#" :value="lang" @click="changeLanguage(lang)">{{ langs[lang] }}</b-dropdown-item>
    </b-dropdown>
</template>

<script>

export default {
  data () {
    return {
      langs: {
        es: 'Castellano',
        ca: 'Català',
        de: 'Deutsch',
        en: 'English',
        eu: 'Euskara',
        fr: 'Français',
        ru: 'Русский'
      }
    }
  },
  methods: {
    changeLanguage (lang) {
      localStorage.language = lang
      this.$i18n.locale = lang
    }
  }
}
</script>
