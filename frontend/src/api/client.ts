// backend との通信の共通処理。/api/ へのリクエストは Vite のプロキシで Django に転送される

const BASE_PATH = '/api'

/** backend がエラーを返したとき、または通信できなかったときのエラー */
export class ApiError extends Error {
  readonly status: number
  /** backend が返したエラー応答の本体（エラー文以外の情報を取り出すため） */
  readonly data: unknown

  constructor(status: number, message: string, data: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_PATH}${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'サーバーに接続できませんでした')
  }

  if (response.status === 204) {
    return undefined as T
  }

  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(data, response.status), data)
  }
  return data as T
}

/** backend のエラー応答（{ error } または DRF の { detail }）から、表示する文を取り出す */
function errorMessage(data: unknown, status: number): string {
  if (data && typeof data === 'object') {
    const { error, detail } = data as { error?: unknown; detail?: unknown }
    if (typeof error === 'string') return error
    if (typeof detail === 'string') return detail
  }
  return `エラーが発生しました（${status}）`
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  delete: <T = void>(path: string) => request<T>('DELETE', path),
}
