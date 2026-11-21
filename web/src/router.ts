import { createRouter, createWebHistory } from 'vue-router'
import homeRouter from './home/router'


const router = createRouter({
    history: createWebHistory(),
    routes: [
        homeRouter
    ]
})

export default router



