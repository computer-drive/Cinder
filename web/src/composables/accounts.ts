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

export async function getAllAccounts(): Promise<ApiResponse<GetAllAccountsResponse>> {
    const response = await request.get<ApiResponse<GetAllAccountsResponse>>("/accounts/getAll", {
        responseType: 'json',
    })
    
    return response.data
}

export async function deleteAccount(account: Account) {
    const response = await request.post<ApiResponse<null>>("/accounts/delete", {
        accountID: account.id,
    })

    if (response.data.status === 0) {
        return true
    }
    return false
}

export async function refreshAccount(account: Account) {
    const response = await request.post<ApiResponse<any>>("/accounts/refresh", {
        accountID: account.id,
    })

    return response
}

