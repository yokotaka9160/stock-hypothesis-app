import { ORDER_TYPE_LABELS, parsedItems } from '../hypothesisFormat'
import { formatPnl, pnlClass } from '../moneyFormat'
import type { Session, VerificationRun } from '../types'

const SESSION_LABELS: Record<Session, string> = {
  pre: '市場前',
  regular: '市場中',
  post: '市場後',
  night: '夜間',
}

const usdPlain = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const easternTime = new Intl.DateTimeFormat('ja-JP', {
  timeZone: 'America/New_York',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
})

interface Props {
  run: VerificationRun
}

/** 右セクションの検証結果（FR-006、FR-007、FR-009） */
export function ResultPanel({ run }: Props) {
  return (
    <div className="result-panel">
      <dl className="result-summary">
        <dt>検証した仮説</dt>
        <dd>
          <p className="hypothesis-text">{run.hypothesis_text}</p>
          <dl className="parsed-items">
            {parsedItems(run.hypothesis_parsed).map(([label, value]) => (
              <div key={label} className="parsed-row">
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </dd>
        <dt>検証期間</dt>
        <dd>
          {run.period_start} 〜 {run.period_end}
        </dd>
        <dt>購入金額</dt>
        <dd>{usdPlain.format(Number(run.amount))}（1回の取引あたり）</dd>
        <dt>総取引回数</dt>
        <dd className="total">{run.total_trade_count} 回</dd>
        <dt>損益額</dt>
        <dd className={`total ${pnlClass(run.total_pnl)}`}>{formatPnl(run.total_pnl)}</dd>
      </dl>
      {run.symbol_results.length > 1 && (
        <p className="hint">総取引回数と損益額は、検証不可の銘柄を除いた全銘柄の合計です。</p>
      )}

      <h3>銘柄ごとの結果</h3>
      <div className="table-wrap">
        <table className="symbol-table">
          <thead>
            <tr>
              <th>銘柄</th>
              <th>取引回数</th>
              <th>損益額</th>
            </tr>
          </thead>
          <tbody>
            {run.symbol_results.map((r) => (
              <tr key={r.symbol}>
                <th scope="row">{r.symbol}</th>
                {r.unavailable ? (
                  <td colSpan={2} className="unavailable">
                    検証不可（データが取れませんでした）
                  </td>
                ) : (
                  <>
                    <td>{r.trade_count} 回</td>
                    <td className={pnlClass(r.pnl)}>{formatPnl(r.pnl)}</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {run.symbol_results
        .filter((r) => r.missing_dates.length > 0)
        .map((r) => (
          <p key={r.symbol} className="missing-dates">
            {r.symbol}：データが欠けている日があります（{r.missing_dates.join('、')}）。データがある分だけで検証しました。
          </p>
        ))}

      {run.symbol_results
        .filter((r) => r.trades.length > 0)
        .map((r) => (
          <details key={r.symbol} className="trades">
            <summary>
              {r.symbol} の取引（{r.trade_count} 回）
            </summary>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>購入（米国東部時間）</th>
                    <th>時間帯</th>
                    <th>購入方法</th>
                    <th>購入価格</th>
                    <th>株数</th>
                    <th>売却（米国東部時間）</th>
                    <th>売却価格</th>
                    <th>損益額</th>
                  </tr>
                </thead>
                <tbody>
                  {r.trades.map((t) => (
                    <tr key={t.buy_at}>
                      <td>{easternTime.format(new Date(t.buy_at))}</td>
                      <td>{SESSION_LABELS[t.buy_session]}</td>
                      <td>{ORDER_TYPE_LABELS[t.order_type]}</td>
                      <td>{Number(t.buy_price).toFixed(2)}</td>
                      <td>{t.quantity}</td>
                      <td>{easternTime.format(new Date(t.sell_at))}</td>
                      <td>{Number(t.sell_price).toFixed(2)}</td>
                      <td className={pnlClass(t.pnl)}>{formatPnl(t.pnl)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        ))}
    </div>
  )
}
