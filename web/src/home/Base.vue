<template>
    <div class="container">
        <div class="aside">
            
            <el-menu  
                class="aside__menu"
                :default-active="route.name"
            >   
                <h1 class="aside__title">CiNDER</h1>
                
                <el-menu-item 
                    v-for="item in homeRouters.children" 
                    :key="item.name"
                    :index="item.name"
                    @click="router.push(item.path)"
                >
                    {{ item.name }}
                </el-menu-item>
            </el-menu>
        </div>
        <div class="main">
            <RouterView/>
        </div>
    </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import homeRouters from './router'

const route = useRoute()
const router = useRouter()


</script>

<style scoped>
.container {
    width: 100dvw;
    height: 100dvh;
    display: flex;
    gap: 10px;
    overflow: hidden;
}

.aside {
    box-sizing: border-box;
    height: 100dvh;
    min-width: 15%;
}

.aside__title {
    padding-left: 15px;
    padding-top: 20px;
    padding-bottom: 20px;
    margin: 0;
}


.aside__menu {
    height: 100%
}



.main {
    flex: 1;
    padding: 20px;
}

</style>