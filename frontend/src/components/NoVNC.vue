<template>
  <div ref='screen' :style='`height: ${this.height}; cursor: pointer;`' />
</template>

<script>
import RFB from '@novnc/novnc/core/rfb'

export default {
  props: {
    height: {
      type: String,
      required: true
    },
    desktop: {
      type: Object,
      required: true
    },
    viewOnly: {
      type: Boolean,
      required: true
    },
    qualityLevel: {
      type: Number,
      required: true
    }
  },
  methods: {
    newRFB (target, viewOnly, qualityLevel) {
      this.rfb = new RFB(
        target,
        'wss://' +
          this.desktop.viewer.values.host +
          ':' +
          this.desktop.viewer.values.port +
          '/' +
          this.desktop.viewer.values.vmHost +
          '/' +
          this.desktop.viewer.values.vmPort,
        {
          credentials: { password: this.desktop.viewer.values.token }
        }
      )

      this.rfb.viewOnly = viewOnly
      this.rfb.qualityLevel = qualityLevel
      this.rfb.scaleViewport = true
    }
  },
  mounted () {
    this.newRFB(this.$refs.screen, this.viewOnly, this.qualityLevel)
  }
}
</script>
