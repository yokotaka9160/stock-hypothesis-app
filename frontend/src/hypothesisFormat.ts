// 読み取り結果を画面に表示する文（FR-024、FR-025）

import type { OrderType, ParsedHypothesis, Quarter } from './types'

/** トリガー条件の文。四半期の指定がなければ、すべての四半期の決算発表が対象（FR-025） */
export function triggerLabel(quarter: Quarter | null): string {
  const target = quarter === null ? '決算発表（すべての四半期）' : `第${quarter}四半期の決算発表`
  return `${target}時刻を含む1時間足の、1本前の1時間足が確定したとき`
}

export const SELL_LABEL =
  '購入が市場前・市場後なら、市場前の最後の1時間足の終値で全売却。購入が市場中なら、市場中の最後の1時間足の終値で全売却'

export const ORDER_TYPE_LABELS: Record<OrderType, string> = {
  stop: '逆指値',
  limit: '指値',
}

export function formatPercent(percent: number): string {
  return `${percent > 0 ? '+' : ''}${percent}%`
}

export function buyConditionLabel(percent: number): string {
  return `トリガーの1時間足の終値から ${formatPercent(percent)} の価格`
}

/** 4つの項目（トリガー条件・購入条件・購入方法・売却条件）を、表示する順に返す */
export function parsedItems(parsed: ParsedHypothesis): Array<[string, string]> {
  return [
    ['トリガー条件', triggerLabel(parsed.trigger.quarter)],
    ['購入条件', buyConditionLabel(parsed.buy_percent)],
    ['購入方法', ORDER_TYPE_LABELS[parsed.order_type]],
    ['売却条件', SELL_LABEL],
  ]
}
