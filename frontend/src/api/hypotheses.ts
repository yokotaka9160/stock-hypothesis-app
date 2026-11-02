import type { Hypothesis, ParsedHypothesis } from '../types'
import { ApiError, api } from './client'

export interface ParseResult {
  text: string
  parsed: ParsedHypothesis
}

/** 範囲外と判定されたときの、範囲に合うように補った文章の提案（FR-026） */
export interface Suggestion {
  text: string
  note: string | null
}

/** 読み取りに失敗したときのエラーから、提案を取り出す */
export function suggestionOf(e: unknown): Suggestion | null {
  const data = e instanceof ApiError ? e.data : null
  if (!data || typeof data !== 'object') return null
  const { suggestion } = data as { suggestion?: unknown }
  if (!suggestion || typeof suggestion !== 'object') return null
  const { text, note } = suggestion as { text?: unknown; note?: unknown }
  if (typeof text !== 'string' || text.trim() === '') return null
  return { text, note: typeof note === 'string' ? note : null }
}

/** 文章を読み取る。保存はしない（FR-017） */
export const parseHypothesis = (text: string) => api.post<ParseResult>('/hypotheses/parse/', { text })

export const listHypotheses = () => api.get<Hypothesis[]>('/hypotheses/')

export const createHypothesis = (text: string, parsed: ParsedHypothesis) =>
  api.post<Hypothesis>('/hypotheses/', { text, parsed })

export const updateHypothesis = (id: number, text: string, parsed: ParsedHypothesis) =>
  api.put<Hypothesis>(`/hypotheses/${id}/`, { text, parsed })

export const deleteHypothesis = (id: number) => api.delete(`/hypotheses/${id}/`)
