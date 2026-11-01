import { useState } from 'react'
import { ORDER_TYPE_LABELS, SELL_LABEL, triggerLabel } from '../hypothesisFormat'
import type { OrderType, ParsedHypothesis } from '../types'

interface Props {
  text: string
  parsed: ParsedHypothesis
  isSaving: boolean
  error: string | null
  onConfirm: (parsed: ParsedHypothesis) => void
  onBack: () => void
}

/** 読み取り結果の確認画面（FR-017）。購入条件の % と購入方法だけを書き換えられる（FR-021） */
export function ParsedConfirm({ text, parsed, isSaving, error, onConfirm, onBack }: Props) {
  const [percentInput, setPercentInput] = useState(String(parsed.buy_percent))
  const [orderType, setOrderType] = useState<OrderType>(parsed.order_type)

  const percent = Number(percentInput)
  const isPercentValid = percentInput.trim() !== '' && Number.isFinite(percent) && percent > -100

  return (
    <div className="parsed-confirm">
      <h3>読み取り結果の確認</h3>
      <p className="confirm-text">{text}</p>
      <dl className="parsed-items">
        <dt>トリガー条件</dt>
        <dd>{triggerLabel(parsed.trigger.quarter)}</dd>

        <dt>
          <label htmlFor="buy-percent">購入条件</label>
        </dt>
        <dd>
          トリガーの1時間足の終値から{' '}
          <input
            id="buy-percent"
            type="number"
            step="0.1"
            value={percentInput}
            onChange={(e) => setPercentInput(e.target.value)}
            disabled={isSaving}
            aria-invalid={!isPercentValid}
          />{' '}
          % の価格
          {!isPercentValid && <span className="field-error">-100 より大きい数を入力してください</span>}
        </dd>

        <dt>
          <label htmlFor="order-type">購入方法</label>
        </dt>
        <dd>
          <select
            id="order-type"
            value={orderType}
            onChange={(e) => setOrderType(e.target.value as OrderType)}
            disabled={isSaving}
          >
            {(Object.keys(ORDER_TYPE_LABELS) as OrderType[]).map((type) => (
              <option key={type} value={type}>
                {ORDER_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </dd>

        <dt>売却条件</dt>
        <dd>{SELL_LABEL}</dd>
      </dl>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button
          type="button"
          onClick={() => onConfirm({ ...parsed, buy_percent: percent, order_type: orderType })}
          disabled={isSaving || !isPercentValid}
        >
          {isSaving ? '保存中…' : 'この内容で保存'}
        </button>
        <button type="button" className="secondary" onClick={onBack} disabled={isSaving}>
          文章を修正する
        </button>
      </div>
    </div>
  )
}
