import { useEffect, useState } from 'react'
import { messageOf } from '../api/client'
import { listVerifications, runVerification } from '../api/verifications'
import type { Hypothesis, VerificationRequest, VerificationRun } from '../types'
import { ResultPanel } from './ResultPanel'
import { VerifyForm } from './VerifyForm'

interface Props {
  hypotheses: Hypothesis[]
  selectedId: number | null
  onSelect: (id: number | null) => void
}

/** 右セクション（User Story 2）。仮説を選ぶと、その仮説の最新の検証結果を表示する */
export function VerificationSection({ hypotheses, selectedId, onSelect }: Props) {
  const [run, setRun] = useState<VerificationRun | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  // 仮説を選び直したら、その仮説の最新の検証結果を読み込む
  useEffect(() => {
    if (selectedId === null) return
    let cancelled = false
    listVerifications(selectedId)
      .then((runs) => {
        if (cancelled) return
        const latest = runs[0] ?? null
        setRun(latest?.status === 'success' ? latest : null)
        setError(latest?.status === 'failed' ? latest.error_message : null)
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(messageOf(e))
      })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const handleSelect = (id: number | null) => {
    setRun(null)
    setError(null)
    onSelect(id)
  }

  const handleSubmit = async (request: VerificationRequest) => {
    setIsRunning(true)
    setError(null)
    try {
      setRun(await runVerification(request))
    } catch (e) {
      // 検証が失敗したときは、エラー文を表示する（T027）
      setRun(null)
      setError(messageOf(e))
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="verification-section">
      <VerifyForm
        hypotheses={hypotheses}
        selectedId={selectedId}
        isRunning={isRunning}
        onSelect={handleSelect}
        onSubmit={handleSubmit}
      />
      {error && (
        <p className="form-error verify-error" role="alert">
          検証に失敗しました：{error}
        </p>
      )}
      {selectedId !== null && run && !isRunning && <ResultPanel run={run} />}
      {selectedId === null && <p className="empty">仮説を選んで検証すると、ここに結果が表示されます。</p>}
    </div>
  )
}
