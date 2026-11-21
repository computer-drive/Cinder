<template>
    <h1>账户</h1>

    <el-divider></el-divider>

    <el-button type="primary" :icon="Plus">添加账户</el-button>

    <div class="accounts-list">

        <el-card v-for="account in accounts" :key="account.id" shadow="never">
            {{ account.name }}
        </el-card>
    </div>
    
</template>

<style scoped>
.accounts-list {
    margin-top: 20px;

    display: flex;
    flex-direction: column;
    gap: 10px;
}
</style>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
import { ref, onMounted } from 'vue'

import { getAllAccounts, type Account } from '../composables/accounts'

const accounts = ref<Account[]>([])

onMounted(async () => {
    const result = await getAllAccounts()
    accounts.value = result.data.accounts

})


</script>
