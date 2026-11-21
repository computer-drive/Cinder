import Home from './Home.vue'
import Accounts from './Accounts.vue'
import Base from './Base.vue'

import { type RouteRecordRaw } from 'vue-router'


const homeRouter: RouteRecordRaw = {
    path: "/",
    component: Base,
    children: [
        {
            path: '/home',
            name: "主页",
            component: Home
        },
        {
            path: '/accounts',
            name: "账号",
            component: Accounts
        }
    ]
}

export default homeRouter

