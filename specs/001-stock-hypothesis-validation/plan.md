# Implementation Plan: 株式取引 仮説検証

**Branch**: `001-stock-hypothesis-validation` | **Date**: 2026-10-30 | **Spec**: specs/001-stock-hypothesis-validation/spec.md

## Summary

米国株の売買仮説を保存し、1時間足の過去データでシミュレーション検証を行い、
結果と仮説の問題点を表示する Web アプリ。
株価データは [検証] を押したときに、DB にないものだけ yfinance から取得して保存する。
検証には DB に保存したデータだけを使うことで、再現性を守る。

## Technical Context

**Language/Version**: Python 3.12、TypeScript 5.x
**Primary Dependencies**:
  - バックエンド：Django、Django REST Framework、yfinance、pandas、
    Google Gen AI SDK（google-genai）（Gemini API を呼び出すため）
  - フロントエンド：React、Vite
**Performance Goals**: [検証] を押してから10分以内に結果を表示する
**Storage**: SQLite
**Testing**: pytest、pytest-django。テストは実装の後に書き、再現性の確認を中心とする。期待値との比較は行わない（原則I）
**Target Platform**: 自分の PC（WSL Ubuntu）上で Docker（docker compose）で起動し、ブラウザから localhost で開く。SQLite のファイルは Docker のボリュームに置き、コンテナを作り直しても消えないようにする
**Project Type**: Web アプリ（バックエンド＋フロントエンド）
**Constraints**:
  - 株価データは1時間足、取得できる期間は直近2年程度
  - 株価データは無料で取得できるもの（yfinance）を使う
  - 実際のお金を用いた取引は行わない
  - 検証には DB に保存した株価データだけを使う
  - Gemini API は無料枠の範囲で使う（回数・速度の上限がある）
  - Gemini API の APIキーは、コードに書かず環境変数で管理する
  - Gemini API から60秒以内に応答がない場合は「応答なし」とみなす
**Scale/Scope**: 利用者は1人。機能は3つ

## Constitution Check

| 原則 | 確認内容 | 結果 |
|---|---|---|
| I. 検証結果の正確性 | 再現性のテストを pytest で行う | ✅ |
| II. 定量的な結果の提示 | 仮説・期間・総取引回数・損益額を表示する | ✅ |
| III. 問題点の提示 | 3つの観点＋取引回数で判定し、理由と改善案を表示する | ✅ |
| IV. 再現性 | DB に保存したデータだけで検証。生成AIの提案内容は例外 | ✅ |
| 制約：有料サービスなし | yfinance と Gemini API の無料枠のみ | ✅ |
| V. シンプルさ | 機能は3つ。データ取得は内部処理 | ⚠️ React の採用（Complexity Tracking を参照） |
| 制約：実取引なし | 発注機能を作らない | ✅ |
| 制約：無料データ | yfinance を使う | ✅ |

## Project Structure

```text
backend/
├── config/            # Django の設定
├── hypotheses/        # 仮説の保存・編集・削除
├── marketdata/        # 株価データの取得・保存（内部処理）
├── simulation/        # シミュレーションと損益計算
├── issues/            # 仮説の問題点の判定
├── advisor/           # Gemini による改善案の提案
├── tests/
└── Dockerfile
frontend/
├── src/
│   ├── components/    # 左セクション（仮説・問題点）、右セクション（検証結果）
│   ├── api/           # バックエンドとの通信
│   └── App.tsx
├── package.json
└── Dockerfile
compose.yaml           # backend と frontend をまとめて起動する

## Complexity Tracking

| 原則に対して増える複雑さ | 必要な理由 |
|---|---|
| React の採用（原則V シンプルさ） | 左右2分割の画面（左：仮説・問題点、右：検証結果）を、画面を読み込み直さずに動的に更新するため |
