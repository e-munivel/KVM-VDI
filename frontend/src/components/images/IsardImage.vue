<template>
  <div class="image-wrapper">
    <b-img
      :class="imageClass"
      thumbnail
      fluid
      :src="`..${imageUrl}`"
      @click="$emit('imageClicked')">
    </b-img>
  </div>
</template>

<script>
export default {
  props: {
    imageUrl: String,
    imageId: String,
    imageClass: String
  }
}
</script>
