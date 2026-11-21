<template>
    主页
    </template> 

<script setup lang="ts">
import { ref } from 'vue'

const routerName = ref('主页')

defineExpose({
    routerName
})

</script>