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

/** 時間帯（FR-016） */
export type Session = 'pre' | 'regular' | 'post' | 'night'

// 金額・価格は桁落ちを避けるため、backend から文字列で受け取る

export interface Trade {
  buy_at: string
  buy_price: string
  buy_session: Session
  order_type: OrderType
  quantity: number
  sell_at: string
  sell_price: string
  pnl: string
}

export interface SymbolResult {
  symbol: string
  trade_count: number
  pnl: string
  unavailable: boolean
  missing_dates: string[]
  trades: Trade[]
}

/** 問題点の観点（FR-010-1〜FR-010-4） */
export type IssueAspect = 'time_of_day' | 'trigger' | 'trigger_value' | 'trade_count'

export interface Issue {
  id: number
  aspect: IssueAspect
  reason: string
}

/** 改善案。numeric は % の再検証（FR-010-5）、ai は Gemini の提案で未検証（FR-010-7） */
export interface Improvement {
  id: number
  issue: number | null
  kind: 'numeric' | 'ai'
  proposal: string
  buy_percent: string | null
  order_type: OrderType | ''
  result_pnl: string | null
  result_trade_count: number | null
  note: string
  /** この改善案から新しい仮説を作るときに、入力欄に入れる文章 */
  draft_text: string
}

export interface VerificationRun {
  id: number
  hypothesis: number
  hypothesis_text: string
  hypothesis_parsed: ParsedHypothesis
  symbols: string[]
  period_start: string
  period_end: string
  amount: string
  status: 'success' | 'failed'
  error_message: string
  created_at: string
  total_trade_count: number
  total_pnl: string
  symbol_results: SymbolResult[]
  issues: Issue[]
  improvements: Improvement[]
}

export interface VerificationRequest {
  hypothesis_id: number
  symbols: string[]
  period_start: string
  period_end: string
  amount: string
}
