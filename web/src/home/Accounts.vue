<template>
    <h1>账户</h1>

    <el-divider></el-divider>

    <el-button type="primary" :icon="Plus">添加账户</el-button>

    <div class="accounts-list">

        <el-card 
        v-for="account in accounts" 
        :key="account.id" 
        shadow="hover"
        >
            <div class="card" v-loading="loadingState.get(account)">
                <div class="card__left">
                    <el-icon><User /></el-icon>

                    <div class="card__content">
                        <p class="card__name">{{ account.name }}</p>
                        <p class="card__description">{{ account.kind === "microsoft" ? "正版账号" : 
                           account.kind === "offline" ? "离线账号" : "第三方认证"
                        }}
                         {{ account.kind === "microsoft" ? `UUID：${account.uuid}`: ""}}
                        </p>
                    </div>
                </div>
                <div class="card__action">
                     <el-tooltip content="刷新账户" v-if="account.kind === 'microsoft'">

                        <el-button 
                            :icon="Refresh" 
                            circle 
                            size="large" 
                            @click="handleRefreshAccount(account)"
                            
                        ></el-button>

                    </el-tooltip>

                    <el-tooltip content="删除账户">
                        <el-button :icon="Delete" circle size="large" @click="handleDeleteAccount(account)"></el-button>  
                    </el-tooltip>

                </div>
            </div>
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

.card {
    display: flex;
    align-items: center;
}

.card__action {
    margin-left: auto;

    /* 隐藏删除按钮 */
    opacity: 0;
    transition: opacity 0.4s ease;
}

.card__left {
    display: flex;
    gap: 8px;
    align-items: center;
}

.card__content {
    display: block
}

.card__content p {
    margin: 0;
}

.card__name {
    font-size: 16px;
    padding-bottom: 4px;
}

.card__description {
    font-size: 12px;
}


.card:hover .card__action {
    opacity: 1;
}


</style>

<script setup lang="ts">
import { Plus, User, Delete, Refresh } from '@element-plus/icons-vue'
import { ref, onMounted, type Ref } from 'vue'

import { ElMessage, ElMessageBox } from 'element-plus'

import { getAllAccounts, type Account, deleteAccount, refreshAccount } from '../composables/accounts'

const accounts = ref<Account[]>([])

const loadingState: Ref<Map<Account, boolean>> = ref(new Map())

onMounted(async () => {
    const result = await getAllAccounts()
    accounts.value = result.data.accounts

})

const handleRefreshAccount = async (account: Account) => {
    loadingState.value.set(account, true)
    try {
        const result = await refreshAccount(account)

        if (result.data.status === 0) {
            ElMessage.success("刷新成功。")
        } else if (result.data.status === 11) {
            ElMessage.error("令牌已过期，请重新登录。")
            
        } else if (result.data.status === 13) {
            ElMessage.error(`刷新失败：${result.data}`)
        } else if (result.data.status === 14) {
            ElMessage.info("所有令牌都是有效的。")
        } else {
            ElMessage.error(`未知错误：${result.data.message}`)
        }
    } finally {
        loadingState.value.set(account, false)
    }
}

const handleDeleteAccount = async (account: Account) => {
    try {
        await ElMessageBox.confirm(`确认删除账户 ${account.name} 吗？`, "确认", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
        })
    } catch {
        // 删除被取消
        return
    }

    const success = await deleteAccount(account)
    if (success) {
        ElMessage.success("删除成功。")

        accounts.value = accounts.value.filter((acc) => acc.id !== account.id)
        loadingState.value.delete(account)
    } else {
        ElMessage.error("删除失败。")
    }

    
}


</script>
