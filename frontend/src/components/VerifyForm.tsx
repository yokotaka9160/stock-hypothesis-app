import { useState } from 'react'
import type { Hypothesis, VerificationRequest } from '../types'

interface Props {
  hypotheses: Hypothesis[]
  selectedId: number | null
  isRunning: boolean
  onSelect: (id: number | null) => void
  onSubmit: (request: VerificationRequest) => void
}

function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** 「AAPL, MSFT」や「AAPL MSFT」のような入力を、銘柄の一覧にする */
function splitSymbols(input: string): string[] {
  return input
    .split(/[\s,、，]+/)
    .map((s) => s.trim().toUpperCase())
    .filter((s) => s !== '')
}

/** 検証の条件の入力（FR-004）。銘柄（複数可）・検証期間・購入金額を指定して [検証] を押す */
export function VerifyForm({ hypotheses, selectedId, isRunning, onSelect, onSubmit }: Props) {
  const [symbolsInput, setSymbolsInput] = useState('')
  // 初期値は、今日までの1年間
  const [periodStart, setPeriodStart] = useState(() => {
    const today = new Date()
    return isoDate(new Date(today.getFullYear() - 1, today.getMonth(), today.getDate()))
  })
  const [periodEnd, setPeriodEnd] = useState(() => isoDate(new Date()))
  const [amount, setAmount] = useState('10000')

  const symbols = splitSymbols(symbolsInput)
  const amountNumber = Number(amount)
  const canSubmit =
    selectedId !== null &&
    symbols.length > 0 &&
    periodStart !== '' &&
    periodEnd !== '' &&
    Number.isFinite(amountNumber) &&
    amountNumber > 0 &&
    !isRunning

  return (
    <form
      className="verify-form"
      onSubmit={(e) => {
        e.preventDefault()
        if (!canSubmit || selectedId === null) return
        onSubmit({
          hypothesis_id: selectedId,
          symbols,
          period_start: periodStart,
          period_end: periodEnd,
          amount,
        })
      }}
    >
      <div className="field">
        <label htmlFor="verify-hypothesis">検証する仮説</label>
        <select
          id="verify-hypothesis"
          value={selectedId ?? ''}
          onChange={(e) => onSelect(e.target.value === '' ? null : Number(e.target.value))}
          disabled={isRunning}
        >
          <option value="">選んでください</option>
          {hypotheses.map((h) => (
            <option key={h.id} value={h.id}>
              {h.text.length > 50 ? `${h.text.slice(0, 50)}…` : h.text}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="verify-symbols">銘柄（米国株。複数の場合はカンマか空白で区切る）</label>
        <input
          id="verify-symbols"
          type="text"
          value={symbolsInput}
          onChange={(e) => setSymbolsInput(e.target.value)}
          placeholder="例：AAPL, MSFT"
          disabled={isRunning}
        />
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="verify-start">検証期間の開始日</label>
          <input
            id="verify-start"
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
            disabled={isRunning}
          />
        </div>
        <div className="field">
          <label htmlFor="verify-end">終了日</label>
          <input
            id="verify-end"
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
            disabled={isRunning}
          />
        </div>
      </div>
      <p className="hint">株価データは直近730日分のみ使えます。</p>
      <div className="field">
        <label htmlFor="verify-amount">購入金額（1回の取引あたり、米ドル）</label>
        <input
          id="verify-amount"
          type="number"
          min="0.01"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          disabled={isRunning}
        />
      </div>
      <div className="form-actions">
        <button type="submit" disabled={!canSubmit}>
          {isRunning ? '検証中…（最大10分）' : '検証'}
        </button>
      </div>
    </form>
  )
}
