# Implementation Plan: 株式取引 仮説検証

**Branch**: `001-hypothesis-verification` | **Date**: 2026-10-30 | **Spec**: specs/001-hypothesis-verification/spec.md

## Summary

米国株の売買仮説を保存し、1時間足の過去データでシミュレーション検証を行い、
結果と仮説の問題点を表示する Web アプリ。
株価データは [検証] を押したときに、DB にないものだけ yfinance から取得して保存する。
検証には DB に保存したデータだけを使うことで、再現性を守る。

## Technical Context

**Language/Version**: Python 3.12（仮）、TypeScript 5.x（仮）
**Primary Dependencies**:
  - バックエンド：Django、Django REST Framework（仮：React と通信する API のため）、yfinance、pandas（仮）
  - フロントエンド：React、Vite（仮：React の開発環境を作るため）
**Storage**: SQLite（仮）
**Testing**: pytest、pytest-django（仮）。テストは実装の後に書き、再現性の確認を中心とする
**Target Platform**: 自分の PC（WSL Ubuntu）上で動かし、ブラウザから localhost で開く
**Project Type**: Web アプリ（バックエンド＋フロントエンド）
**Performance Goals**: [NEEDS CLARIFICATION: 検証結果が表示されるまでの許容時間]
**Constraints**:
  - 株価データは1時間足、取得できる期間は直近2年程度
  - 株価データは無料で取得できるもの（yfinance）を使う
  - 実際のお金を用いた取引は行わない
  - 検証には DB に保存した株価データだけを使う
**Scale/Scope**: 利用者は1人。機能は3つ

## Constitution Check

| 原則 | 確認内容 | 結果 |
|---|---|---|
| I. 検証結果の正確性 | 再現性のテストを pytest で行う | ✅ |
| II. 定量的な結果の提示 | 仮説・期間・総取引回数・損益額を表示する | ✅ |
| III. 問題点の提示 | 3つの観点で表示する | ⚠️ 判断基準が spec で未定 |
| IV. 再現性 | DB に保存したデータだけで検証する | ✅ |
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
└── tests/
frontend/
├── src/
│   ├── components/    # 左セクション（仮説・問題点）、右セクション（検証結果）
│   ├── api/           # バックエンドとの通信
│   └── App.tsx
└── package.json