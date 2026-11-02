// 金額を画面に表示する形（米ドル）

const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', signDisplay: 'exceptZero' })

/** 損益額。表示は小数点以下2桁に丸める（計算は backend で小数点以下6桁まで行う） */
export function formatPnl(value: string): string {
  return usd.format(Number(value))
}

export function pnlClass(value: string): string {
  const n = Number(value)
  return n > 0 ? 'pnl positive' : n < 0 ? 'pnl negative' : 'pnl'
}
