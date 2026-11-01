import { parsedItems } from '../hypothesisFormat'
import type { Hypothesis } from '../types'

interface Props {
  hypotheses: Hypothesis[]
  editingId: number | null
  disabled: boolean
  onEdit: (hypothesis: Hypothesis) => void
  onDelete: (hypothesis: Hypothesis) => void
}

/** 保存した仮説の一覧。入力された文章と読み取り結果の両方を表示する（FR-024） */
export function HypothesisList({ hypotheses, editingId, disabled, onEdit, onDelete }: Props) {
  if (hypotheses.length === 0) {
    return <p className="empty">まだ仮説がありません。</p>
  }

  return (
    <ul className="hypothesis-list">
      {hypotheses.map((h) => (
        <li key={h.id} className={h.id === editingId ? 'hypothesis-item editing' : 'hypothesis-item'}>
          <p className="hypothesis-text">{h.text}</p>
          <dl className="parsed-items">
            {parsedItems(h.parsed).map(([label, value]) => (
              <div key={label} className="parsed-row">
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          <div className="item-actions">
            <button type="button" className="secondary" onClick={() => onEdit(h)} disabled={disabled}>
              編集
            </button>
            <button type="button" className="danger" onClick={() => onDelete(h)} disabled={disabled}>
              削除
            </button>
          </div>
        </li>
      ))}
    </ul>
  )
}
