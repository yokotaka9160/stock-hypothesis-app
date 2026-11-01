import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { messageOf } from './api/client'
import { listHypotheses } from './api/hypotheses'
import { HypothesisSection } from './components/HypothesisSection'
import { VerificationSection } from './components/VerificationSection'
import type { Hypothesis } from './types'

function App() {
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  // 右セクションで検証する仮説
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const reload = useCallback(async () => {
    try {
      setHypotheses(await listHypotheses())
      setLoadError(null)
    } catch (e) {
      setLoadError(messageOf(e))
    }
  }, [])

  // 画面を開いたときに、保存済みの仮説を読み込む（FR-002）
  useEffect(() => {
    let cancelled = false
    listHypotheses()
      .then((items) => {
        if (!cancelled) setHypotheses(items)
      })
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(messageOf(e))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>株式取引 仮説検証</h1>
      </header>
      <main className="app-main">
        {/* 左セクション：仮説の入力・一覧と、検証仮説の下に問題点（理由）・改善案 */}
        <section className="panel panel-left" aria-labelledby="left-title">
          <h2 id="left-title">仮説</h2>
          <HypothesisSection
            hypotheses={hypotheses}
            loadError={loadError}
            onChanged={reload}
            onDeleted={(id) => {
              if (id === selectedId) setSelectedId(null)
            }}
          />
        </section>
        {/* 右セクション：検証の条件と検証結果 */}
        <section className="panel panel-right" aria-labelledby="right-title">
          <h2 id="right-title">検証結果</h2>
          <VerificationSection hypotheses={hypotheses} selectedId={selectedId} onSelect={setSelectedId} />
        </section>
      </main>
    </div>
  )
}

export default App
