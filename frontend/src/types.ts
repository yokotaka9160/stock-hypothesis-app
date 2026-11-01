// backend の hypotheses/parser.py の parsed と同じ形

export type OrderType = 'stop' | 'limit'

/** 決算の四半期（暦年で数える）。null はすべての四半期 */
export type Quarter = 1 | 2 | 3 | 4

export interface ParsedHypothesis {
  trigger: { type: 'earnings_prev_bar_close'; quarter: Quarter | null }
  /** トリガーの1時間足の終値から何 % の価格で買うか（マイナスは下の価格） */
  buy_percent: number
  order_type: OrderType
  sell: { type: 'session_last_bar' }
}

export interface Hypothesis {
  id: number
  text: string
  parsed: ParsedHypothesis
  created_at: string
  updated_at: string
}
