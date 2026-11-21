import { type AxiosInstance } from 'axios'
import axios from 'axios'

export interface ApiResponse<T> {
    status: number
    message: string
    data: T
}

export const request: AxiosInstance = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json;charset=utf-8',
    },
})




