import { formatPnl, pnlClass } from '../moneyFormat'
import type { IssueAspect, VerificationRun } from '../types'

const ASPECT_LABELS: Record<IssueAspect, string> = {
  time_of_day: '時間帯',
  trigger: 'トリガー条件',
  trigger_value: 'トリガー条件の数値',
  trade_count: '取引回数',
}

interface Props {
  run: VerificationRun
  /** 改善案の文章を、仮説の入力欄に入れる（保存は通常の流れで行う） */
  onUseImprovement: (text: string) => void
  disabled: boolean
}

/**
 * 左セクションの検証仮説の下に出す、問題点（理由）と改善案（FR-010）
 * 問題点（なければ「問題は未発見」）、改善案の順に表示する。改善案は問題点の有無にかかわらず表示する。
 */
export function IssuePanel({ run, onUseImprovement, disabled }: Props) {
  const numeric = run.improvements.filter((m) => m.kind === 'numeric')
  const ai = run.improvements.filter((m) => m.kind === 'ai')

  return (
    <div className="issue-panel">
      <p className="issue-run">
        検証（{run.period_start} 〜 {run.period_end}、{run.symbols.join('・')}）の問題点と改善案
      </p>

      <h4>問題点</h4>
      {run.issues.length === 0 ? (
        <p className="no-issue">問題は未発見</p>
      ) : (
        <ul className="issue-list">
          {run.issues.map((issue) => (
            <li key={issue.id}>
              <span className="issue-aspect">{ASPECT_LABELS[issue.aspect]}</span>
              <p>{issue.reason}</p>
            </li>
          ))}
        </ul>
      )}

      <h4>改善案</h4>
      <ul className="improvement-list">
        {numeric.map((m) => (
          <li key={m.id}>
            <span className="improvement-kind">数値（再検証済み）</span>
            <p>{m.proposal}</p>
            {m.result_pnl !== null && (
              <p className="improvement-result">
                再検証の結果：総取引回数 {m.result_trade_count} 回、損益額{' '}
                <span className={pnlClass(m.result_pnl)}>{formatPnl(m.result_pnl)}</span>
              </p>
            )}
            <p className="improvement-note">{m.note}</p>
            <UseButton text={m.draft_text} onUse={onUseImprovement} disabled={disabled} />
          </li>
        ))}
        {ai.map((m) => (
          <li key={m.id}>
            <span className="improvement-kind unverified">時間帯・トリガー（AI の提案・未検証）</span>
            <p>{m.proposal}</p>
            <UseButton text={m.draft_text} onUse={onUseImprovement} disabled={disabled} />
          </li>
        ))}
      </ul>
      {ai.length > 0 && <p className="improvement-note">{ai[0].note}</p>}
    </div>
  )
}

function UseButton({ text, onUse, disabled }: { text: string; onUse: (text: string) => void; disabled: boolean }) {
  return (
    <div className="item-actions">
      <button type="button" className="secondary" onClick={() => onUse(text)} disabled={disabled}>
        この案で新しい仮説を作る
      </button>
    </div>
  )
}
