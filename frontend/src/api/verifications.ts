import type { VerificationRequest, VerificationRun } from '../types'
import { api } from './client'

/** 検証を実行する。最大10分かかる（FR-015） */
export const runVerification = (request: VerificationRequest) => api.post<VerificationRun>('/verifications/', request)

/** 仮説の検証結果を、新しい順に返す */
export const listVerifications = (hypothesisId: number) =>
  api.get<VerificationRun[]>(`/verifications/?hypothesis=${hypothesisId}`)
