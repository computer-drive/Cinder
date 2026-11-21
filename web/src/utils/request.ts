import { type AxiosInstance } from 'axios'
import axios from 'axios'

import { h } from 'vue'
import { ElMessage, ElNotification, ElMessageBox, ElButton } from 'element-plus'

export interface ApiResponse<T> {
    status: number
    message: string
    data: T
}

interface ErrorResponse {
    error: string
    traceback: string[]
}

export const request: AxiosInstance = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json;charset=utf-8',
    },
})

request.interceptors.response.use(
    (response) => {
        return response
    },
    (error) => {
        if (error.response && error.response.status === 500) {
            const response = error.response.data as ErrorResponse
            ElNotification.error({
                title: `未捕获异常：${response.error}`,
                message: () => {
                    return h(ElButton, {
                        // type: 'primary',
                        size: 'small',
                        onClick: () => {
                            ElMessageBox({
                                title: "Traceback",
                                message: h('pre', {
                                    style: 'overflow: auto;'
                                },response.traceback.join('\n')),
                                confirmButtonText: '确定'
                            },
                            )
                        },
            
                    }, '详细信息' )
                },
                
            })
        } else {
            ElMessage.error(`网络错误：${error.message}`)
        }

        return Promise.reject(error)
    }
)




