# Research: 株式取引 仮説検証

**Date**: 2026-10-30
**Spec**: [spec.md](./spec.md)

## 1. 1分足の株価データの取得元（FR-013, FR-015）

- **Decision**: Alpaca Market Data API の無料プラン（Basic）を使い、全市場の約定データ（SIP）から作った1分足を取得する。
- **Rationale**:
  - 無料プランでも、15分以上前の SIP データ（bars / trades / quotes）は有料プランと同じものを取得できる。履歴は 2016 年から、上限は 200 回/分。
  - 取得するときは `feed=sip` を指定し、終了時刻を現在時刻の15分以上前にする（直近15分を含めると 403 エラーになる）。
  - 無料の IEX フィードは全米出来高の約2.5%しか含まないため、価格の判定には使わない。
- **Alternatives considered**:
  - Alpha Vantage `TIME_SERIES_INTRADAY`：時間外（4:00〜20:00 ET）を含み、2000年以降の月を指定できるが、premium エンドポイントで無料では使えない。
  - Polygon（Massive）無料プラン：5回/分の制限があり、取得できる履歴の範囲や時間外を含むかを公式情報で確認できなかった。
- **補足**:
  - 時間外（4:00〜9:30、16:00〜20:00 ET）の1分足が含まれることは公式文書では確認できなかった。実装を始める前に、実データで確認する。
  - 履歴は 2016 年からなので、年1回のトリガー（第1四半期の決算など）は最大でも約10回しか成立しない。FR-010b（成立回数10回未満を問題点として表示）は、ほぼ毎回表示される見込み。
  - 株数（購入金額 ÷ 約定価格）を実際の価格で計算するため、株式分割などで調整していない生の価格を使う。
  - 時刻は米国東部時間（`America/New_York`）で扱い、夏時間の切り替えを考慮する。

## 2. 決算発表の日付と区分の取得元（FR-014）

- **Decision**: Alpha Vantage の `EARNINGS` エンドポイントを使う。
- **Rationale**:
  - 1回の呼び出しで、1銘柄の過去の四半期決算をすべて取得できる（例：IBM は 1996 年から）。
  - 各四半期に `fiscalDateEnding`（決算期末）、`reportedDate`（発表日）、`reportTime`（`pre-market` / `post-market`）が含まれる。決算期末から「第1四半期」を判定できる。
  - 正確な発表時刻はないので、FR-014 のとおり pre-market を 8:00、post-market を 16:00（ET）とみなす。
- **Alternatives considered**:
  - Finnhub の earnings calendar：bmo / amc / dmh の区分を持つが、無料プランで取れる履歴の範囲を確認できなかった。
  - Financial Modeling Prep：BMO / AMC の区分を持ち、無料は 250 回/日。期間指定のカレンダー形式なので、銘柄ごとの全履歴を取るには何度も呼び出す必要がある。
  - FirstRate Data：2000年からの発表時刻区分を持つが有料。
- **補足**:
  - Alpha Vantage の無料キーは 25 回/日程度に制限されている（資料によって数値が違う）。銘柄ごとに1回呼べば足りるので問題ない。ただし、`EARNINGS` を無料キーで使えるかは実際のキーで確認する（demo キーでは取得できた）。
  - `reportTime` が空の回がある場合の扱いは、spec に決めがない。

## 3. 自由な文章から条件への変換方法（FR-001a〜c）

- **Decision**: 大規模言語モデル（Claude API）の構造化出力を使い、文章を「トリガー条件・購入条件・購入方法・注文の有効時間・売却条件」の決まった形式（JSON）に変換する。変換は保存時に1回だけ行い、検証では保存した変換結果だけを使う。
- **Rationale**:
  - 書き方の決まっていない文章を扱えるのは言語モデルだけである。
  - 変換結果は毎回同じとは限らないが、利用者が確認したうえで保存し（FR-001b）、検証では保存した結果を使う（FR-001c）ので、原則IV（再現性）は守れる。
  - 変換先の形式で使える条件の種類（例：決算発表の◯分前、価格の◯%上昇、逆指値）を限ると、シミュレーションできない条件が保存されるのを防げる。形式に当てはまらない文章は、変換できなかった項目として返す。
- **Alternatives considered**:
  - 決まった書き方のルールで読み取る方法：再現性は高いが、決められた書き方しか受け付けないので、選んだ「自由な文章での入力」と合わない。
  - 手元で動く言語モデル：費用はかからないが、変換の精度と動かす環境の準備が負担になる。
- **補足**: Claude API は有料（使った分だけ課金）。constitution の「無料」は株価データについての制約なので違反ではないが、費用がかかる。

## 4. 取得データの保存（FR-011, 原則IV）

- **Decision**: 取得した1分足と決算データは手元に保存し、2回目以降の検証では保存したデータを使う。
- **Rationale**: 取得元のデータは後から修正されることがあり、取得し直すたびに結果が変わると原則IV（再現性）を守れない。取得回数の制限（Alpaca 200 回/分、Alpha Vantage 25 回/日程度）も避けられる。
- **Alternatives considered**: 検証のたびに取得する方法は、再現性が取得元に左右されるため採らない。

## 5. アプリの形と保存先（FR-002, constitution「利用者は個人のみ」）

- **Decision**: 手元のパソコンだけで動くアプリにし、仮説・変換結果・取得データ・検証結果は手元のファイル（SQLite）に保存する。
- **Rationale**: 利用者は開発者本人だけなので、サーバーやログイン機能はいらない。SQLite は1つのファイルで済み、アプリを閉じても仮説が残る（FR-002）。
- **Alternatives considered**: サーバーに置く Web サービスは、利用者が1人なので不要と判断した。
- **補足**: 画面を作る具体的な技術（言語・ライブラリ）は plan.md の Technical Context で決める。

## 参考

- [Alpaca: About Market Data API](https://docs.alpaca.markets/docs/about-market-data-api)
- [Alpaca: Historical Stock Data](https://docs.alpaca.markets/docs/historical-stock-data-1)
- [Alpaca Forum: Free Account/Paper Trading IEX/SIP Questions](https://forum.alpaca.markets/t/free-account-paper-trading-iex-sip-questions/19208)
- [Alpaca Forum: Solutions for getting bars missing due to 15 minute historical delay](https://forum.alpaca.markets/t/solutions-for-getting-bars-missing-due-to-15-minute-historical-delay/8913)
- [Alpha Vantage: Documentation](https://www.alphavantage.co/documentation/)
- [Alpha Vantage: EARNINGS（demo キーでの取得例）](https://www.alphavantage.co/query?function=EARNINGS&symbol=IBM&apikey=demo)
- [Macroption: Alpha Vantage API Request Limits](https://www.macroption.com/alpha-vantage-api-limits/)
- [Alpaca: Polygon と Alpaca のデータプランの違い](https://alpaca.markets/learn/the-top-3-differences-between-polygon-and-alpaca-data-plans/)
- [Eulerpool: Earnings Calendar API ガイド](https://eulerpool.com/blog/earnings-calendar-api-2)
