<template>
  <b-col cols='3'>
    <b-card no-body class='mt-4 mb-2 mx-3'>
      <template v-slot:header>
        <b-row class='pt-2 pl-3 pr-3'>
          <h6 cols='10' class='text-muted'>{{ desktop.userName }}</h6>
          <b-icon cols='2'
            @click="selectDesktop(desktop)"
            icon="arrows-fullscreen"
            scale="1.25"
            class="cursor-pointer ml-auto flex-row d-none d-xl-flex"
          />
        </b-row>
      </template>
      <b-card-body class='pt-0 pb-0 pl-0 pr-0' @click="selectDesktop(desktop)">
        <NoVNC
          v-if='desktop.viewer'
          :height="'200px'"
          :desktop='desktop'
          :viewOnly='true'
          :qualityLevel='0'
        />
        <div v-else style="height: 200px; background-color: black; padding-top: 50px" class="cursor-pointer">
          <div id="deployment-logo" class="rounded-circle bg-red mx-auto d-block align-items-center " style="background-image: url(/custom/logo.svg);background-size: 70px 70px; opacity: 0.5;">
          </div>
          <p class="text-center text-white">{{ $t('views.deployment.desktop.not-available') }}</p>
        </div>
      </b-card-body>
    </b-card>
  </b-col>
</template>
<script>
import NoVNC from '@/components/NoVNC.vue'

export default {
  props: {
    desktop: {
      required: true,
      type: Object
    }
  },
  components: {
    NoVNC
  },
  methods: {
    selectDesktop (desktop) {
      this.$store.dispatch('setSelectedDesktop', desktop)
      this.$store.dispatch('setViewType', 'youtube')
    }
  }
}
</script>
