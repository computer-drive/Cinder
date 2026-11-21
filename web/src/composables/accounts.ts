import { request, type ApiResponse } from '../utils/request'

export interface Account {
    kind: string
    id:  string
    name: string
    uuid: string
}

interface GetAllAccountsResponse {
    accounts: Account[]
}

export async function getAllAccounts() {
    const response = await request.get<ApiResponse<GetAllAccountsResponse>>("/accounts/getAll", {
        responseType: 'json',
    })
    return response.data
}

