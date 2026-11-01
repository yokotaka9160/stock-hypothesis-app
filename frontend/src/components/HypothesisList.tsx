import { parsedItems } from '../hypothesisFormat'
import type { Hypothesis, VerificationRun } from '../types'
import { IssuePanel } from './IssuePanel'

interface Props {
  hypotheses: Hypothesis[]
  editingId: number | null
  verifiedRun: VerificationRun | null
  disabled: boolean
  onUseImprovement: (text: string) => void
  onEdit: (hypothesis: Hypothesis) => void
  onDelete: (hypothesis: Hypothesis) => void
}

/** 保存した仮説の一覧。入力された文章と読み取り結果の両方を表示する（FR-024） */
export function HypothesisList({
  hypotheses,
  editingId,
  verifiedRun,
  disabled,
  onUseImprovement,
  onEdit,
  onDelete,
}: Props) {
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
          {/* 検証した仮説の下に、問題点（理由）と改善案を出す（FR-010） */}
          {verifiedRun?.hypothesis === h.id && (
            <IssuePanel run={verifiedRun} onUseImprovement={onUseImprovement} disabled={disabled} />
          )}
        </li>
      ))}
    </ul>
  )
}
