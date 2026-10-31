# Tasks: 株式取引 仮説検証

**前提**: plan.md、spec.md、data-model.md、research.md

## Phase 1: Setup（準備）

- [ ] T001 backend/ に Django プロジェクト（config）を作る
- [ ] T002 [P] Django アプリ hypotheses / marketdata / simulation / issues / advisor を作る
- [ ] T003 [P] frontend/ に Vite＋React＋TypeScript のプロジェクトを作る
- [ ] T004 [P] backend/ に pytest と pytest-django を設定する
- [ ] T005 [P] Gemini の APIキーを環境変数から読み込む設定と、backend/.env.example を作る
- [ ] T006 Django REST Framework を設定し、frontend から backend に通信できるようにする（Vite のプロキシ機能を使う）

## Phase 2: Foundational（全ストーリーの土台）

- [ ] T007 backend/marketdata/models.py に PriceBar（1時間足）モデルを作る
- [ ] T008 [P] backend/marketdata/models.py に EarningsEvent（決算発表）モデルを作る
- [ ] T009 backend/marketdata/sessions.py に、時間帯（市場前／市場中／市場後／夜間）の判定を作る（夏時間・冬時間に対応。research 項目4）
- [ ] T010 backend/marketdata/services.py に、DB にない株価データ・決算発表データだけを yfinance から取得して保存する処理を作る（保存済みのデータは上書きしない。決算発表の時刻が取れない場合は、市場前 8:00・市場後 16:00 とみなす。FR-014）
- [ ] T011 [P] backend/advisor/client.py に、Gemini を呼び出す共通処理を作る（60秒で応答なし、無料枠の上限はエラーとして扱う）
- [ ] T012 [P] frontend/src/api/client.ts に、backend との通信の共通処理を作る
- [ ] T013 [P] frontend/src/App.tsx に、左右2分割の画面レイアウトを作る

## Phase 3: User Story 1 - 仮説の保存・編集・削除（P1）

- [ ] T014 [US1] backend/hypotheses/models.py に Hypothesis（text・parsed）モデルを作る
- [ ] T015 [US1] backend/hypotheses/parser.py に、Gemini で文章を読み取り、FR-025 の範囲かどうかを確認する処理を作る（範囲外・失敗はエラー。FR-018）
- [ ] T016 [US1] backend/hypotheses/views.py に、読み取り・保存・一覧・編集（もう一度読み取る）・削除の API を作る
- [ ] T017 [P] [US1] frontend/src/components/HypothesisForm.tsx に、例文付きの入力欄と [保存] ボタンを作る
- [ ] T018 [US1] frontend/src/components/ParsedConfirm.tsx に、読み取り結果の確認画面を作る（% と購入方法を書き換えられる。FR-021）
- [ ] T019 [US1] frontend/src/components/HypothesisList.tsx に、文章と読み取り結果の両方を表示する一覧を作る（FR-024）

## Phase 4: User Story 2 - 検証結果の表示（P1）

- [ ] T020 [US2] backend/simulation/models.py に VerificationRun・SymbolResult・Trade モデルを作る
- [ ] T021 [US2] backend/simulation/engine.py に、トリガーの判定、逆指値・指値の約定判定（注文の有効時間＝60分、1時間足ではトリガーの次の1本の足だけ。FR-008、FR-008a、research 項目3）、売却（FR-008b）、株数の切り捨て、0株・未約定の扱い（FR-004a）、1銘柄につき同時に1つの取引（FR-004b）、売却する足のデータが欠けている場合の扱い（FR-008b）を作る
- [ ] T022 [US2] backend/simulation/engine.py に、銘柄ごとの結果と全銘柄合計の計算を作る（FR-007）
- [ ] T023 [US2] データが取れない銘柄・夜間の取引を、検証不可として扱う処理と、一部の日だけデータが取れない場合に、データがある分だけで検証し、欠けている日があることを表示する処理を作る（FR-009）
- [ ] T024 [US2] backend/simulation/views.py に、検証の API を作る（データ取得 → シミュレーション → 問題点 → AI 提案。Gemini が失敗したら検証全体を失敗にする）
- [ ] T025 [P] [US2] frontend/src/components/VerifyForm.tsx に、銘柄（複数）・期間・購入金額の入力と [検証] ボタンを作る
- [ ] T026 [US2] frontend/src/components/ResultPanel.tsx に、右セクションの検証結果（仮説・期間・総取引回数・損益額、銘柄ごと・合計）を作る
- [ ] T027 [US2] 検証が失敗したときのエラー文の表示を作る

## Phase 5: User Story 3 - 問題点の提示（P2）

- [ ] T028 [US3] backend/issues/models.py に Issue・Improvement モデルを作る
- [ ] T029 [US3] backend/issues/rules.py に、問題点の判定を作る（FR-010-1〜4、問題がないときは FR-010-6。総取引回数が0回のときは FR-010-2・3 を判定しない）
- [ ] T030 [US3] backend/issues/improvements.py に、% を -15%〜+15% で1%刻みに再検証し、全銘柄合計の損益が一番良い1つを改善案として出す処理を作る（問題点の有無にかかわらず出す。同点のときは元の % に近いもの、それも同じなら小さいほう。FR-010-5）
- [ ] T031 [US3] backend/advisor/proposals.py に、Gemini による時間帯・トリガーの提案（3個・未検証）を作る（FR-010-7）
- [ ] T032 [US3] 改善案に、過学習の注意書きと、AI 提案が未検証である旨を付ける（FR-010-8）
- [ ] T033 [US3] frontend/src/components/IssuePanel.tsx に、左セクションの検証仮説の下に、問題点（理由）、問題がない場合は「問題は未発見」、続けて改善案を表示する部分を作る（FR-010）

## Phase 6: Tests（実装の後に書く。constitution 原則I）

- [ ] T034 [P] 同じ条件で2回検証し、結果が完全に一致することを確かめるテスト（FR-011）
- [ ] T035 [P] 改善案（31通り）の再検証結果が、2回とも一致することを確かめるテスト
- [ ] T036 [P] 保存済みの株価データが上書きされないことを確かめるテスト
- [ ] T037 [P] 検証中に yfinance を呼ばず、DB のデータだけを使うことを確かめるテスト（データが揃っている場合）
- [ ] T038 [P] Gemini が失敗・60秒応答なしのとき、検証全体が失敗になることを確かめるテスト

## Phase 7: Polish（仕上げ）

- [ ] T039 検証にかかる時間を測り、10分以内に終わるかを確かめる（FR-015、research 項目8）
- [ ] T040 quickstart.md に、起動と動作確認の手順を書く

## 依存関係

- Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7
- T021 は research 項目3（約定判定）の結論が出てから着手する
- T010 は research 項目1・2・6 の結論が出てから着手する