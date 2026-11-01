import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import {
  createHypothesis,
  deleteHypothesis,
  listHypotheses,
  parseHypothesis,
  updateHypothesis,
  suggestionOf,
  type ParseResult,
  type Suggestion,
} from '../api/hypotheses'
import type { Hypothesis, ParsedHypothesis } from '../types'
import { HypothesisForm } from './HypothesisForm'
import { HypothesisList } from './HypothesisList'
import { ParsedConfirm } from './ParsedConfirm'

function messageOf(e: unknown): string {
  return e instanceof ApiError ? e.message : 'エラーが発生しました'
}

/**
 * 左セクションの仮説の部分（User Story 1）
 * 入力 → [保存] で読み取り → 確認画面で確認・書き換え → 保存、の順に進む（FR-017、FR-021）。
 * 編集も同じ流れで、文章をもう一度読み取ってから保存する（FR-022）。
 */
export function HypothesisSection() {
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  const [editing, setEditing] = useState<Hypothesis | null>(null)
  const [draftText, setDraftText] = useState('')
  // 入力欄を作り直して、draftText を初期値として入れ直すためのキー
  const [formKey, setFormKey] = useState(0)
  const [pending, setPending] = useState<ParseResult | null>(null)

  const [isParsing, setIsParsing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null)
  const [confirmError, setConfirmError] = useState<string | null>(null)

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

  const resetForm = (text: string, target: Hypothesis | null) => {
    setEditing(target)
    setDraftText(text)
    setPending(null)
    setFormError(null)
    setSuggestion(null)
    setConfirmError(null)
    setFormKey((k) => k + 1)
  }

  const handleSubmit = async (text: string) => {
    setDraftText(text)
    setIsParsing(true)
    setFormError(null)
    setSuggestion(null)
    try {
      setPending(await parseHypothesis(text))
      setConfirmError(null)
    } catch (e) {
      // 読み取れない・範囲外・Gemini の失敗の場合は保存しない（FR-018）。範囲外なら補った文章を提案する（FR-026）
      setFormError(messageOf(e))
      setSuggestion(e instanceof ApiError ? suggestionOf(e.data) : null)
    } finally {
      setIsParsing(false)
    }
  }

  const handleConfirm = async (parsed: ParsedHypothesis) => {
    if (!pending) return
    setIsSaving(true)
    setConfirmError(null)
    try {
      if (editing) {
        await updateHypothesis(editing.id, pending.text, parsed)
      } else {
        await createHypothesis(pending.text, parsed)
      }
      resetForm('', null)
      await reload()
    } catch (e) {
      setConfirmError(messageOf(e))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (hypothesis: Hypothesis) => {
    // 仮説を削除すると、その仮説の検証結果も一緒に削除される（FR-003）
    if (!window.confirm('仮説を削除すると、検証結果も削除されますが本当に削除しますか？')) return
    try {
      await deleteHypothesis(hypothesis.id)
      if (editing?.id === hypothesis.id) resetForm('', null)
      await reload()
    } catch (e) {
      setLoadError(messageOf(e))
    }
  }

  const busy = isParsing || isSaving

  return (
    <div className="hypothesis-section">
      {pending ? (
        <ParsedConfirm
          text={pending.text}
          parsed={pending.parsed}
          isSaving={isSaving}
          error={confirmError}
          onConfirm={handleConfirm}
          onBack={() => resetForm(draftText, editing)}
        />
      ) : (
        <HypothesisForm
          key={formKey}
          initialText={draftText}
          isEditing={editing !== null}
          isParsing={isParsing}
          error={formError}
          suggestion={suggestion}
          onSubmit={handleSubmit}
          onCancelEdit={() => resetForm('', null)}
          onUseSuggestion={(text) => resetForm(text, editing)}
        />
      )}

      <h3 className="list-title">保存した仮説</h3>
      {loadError && (
        <p className="form-error" role="alert">
          {loadError}
        </p>
      )}
      <HypothesisList
        hypotheses={hypotheses}
        editingId={editing?.id ?? null}
        disabled={busy || pending !== null}
        onEdit={(h) => resetForm(h.text, h)}
        onDelete={handleDelete}
      />
    </div>
  )
}
