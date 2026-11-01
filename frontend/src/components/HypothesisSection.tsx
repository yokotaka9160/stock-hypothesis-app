import { useRef, useState } from 'react'
import { messageOf } from '../api/client'
import {
  createHypothesis,
  deleteHypothesis,
  parseHypothesis,
  updateHypothesis,
  suggestionOf,
  type ParseResult,
  type Suggestion,
} from '../api/hypotheses'
import type { Hypothesis, ParsedHypothesis, VerificationRun } from '../types'
import { HypothesisForm } from './HypothesisForm'
import { HypothesisList } from './HypothesisList'
import { ParsedConfirm } from './ParsedConfirm'

/**
 * 左セクションの仮説の部分（User Story 1）
 * 入力 → [保存] で読み取り → 確認画面で確認・書き換え → 保存、の順に進む（FR-017、FR-021）。
 * 編集も同じ流れで、文章をもう一度読み取ってから保存する（FR-022）。
 */
interface Props {
  hypotheses: Hypothesis[]
  loadError: string | null
  /** 右セクションに表示中の検証結果。検証した仮説の下に問題点・改善案を出す（FR-010） */
  verifiedRun: VerificationRun | null
  /** 仮説を保存・削除したあとに、一覧を読み込み直す */
  onChanged: () => Promise<void>
  /** 仮説を削除したとき */
  onDeleted: (id: number) => void
  /** 改善案から作った仮説を保存したとき。右セクションで検証できるように選ぶ */
  onCreatedFromImprovement: (id: number) => void
}

export function HypothesisSection({
  hypotheses,
  loadError,
  verifiedRun,
  onChanged,
  onDeleted,
  onCreatedFromImprovement,
}: Props) {
  const sectionRef = useRef<HTMLDivElement>(null)
  // 入力欄の文章が改善案から作ったものか（保存したら、右セクションでその仮説を選ぶ）
  const [fromImprovement, setFromImprovement] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

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

  const resetForm = (text: string, target: Hypothesis | null, fromImprovementText = false) => {
    setEditing(target)
    setDraftText(text)
    setPending(null)
    setFormError(null)
    setSuggestion(null)
    setConfirmError(null)
    setFormKey((k) => k + 1)
    setFromImprovement(fromImprovementText)
  }

  const handleUseImprovement = (text: string) => {
    // 入力欄に入れるだけで、保存は通常の流れ（読み取り → 確認 → 保存）で行う
    resetForm(text, null, true)
    sectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
      setSuggestion(suggestionOf(e))
    } finally {
      setIsParsing(false)
    }
  }

  const handleConfirm = async (parsed: ParsedHypothesis) => {
    if (!pending) return
    setIsSaving(true)
    setConfirmError(null)
    try {
      const created = fromImprovement && !editing
      let saved: Hypothesis
      if (editing) {
        saved = await updateHypothesis(editing.id, pending.text, parsed)
      } else {
        saved = await createHypothesis(pending.text, parsed)
      }
      resetForm('', null)
      await onChanged()
      if (created) onCreatedFromImprovement(saved.id)
    } catch (e) {
      setConfirmError(messageOf(e))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (hypothesis: Hypothesis) => {
    // 仮説を削除すると、その仮説の検証結果も一緒に削除される（FR-003）
    if (!window.confirm('仮説を削除すると、検証結果も削除されますが本当に削除しますか？')) return
    setDeleteError(null)
    try {
      await deleteHypothesis(hypothesis.id)
      if (editing?.id === hypothesis.id) resetForm('', null)
      onDeleted(hypothesis.id)
      await onChanged()
    } catch (e) {
      setDeleteError(messageOf(e))
    }
  }

  const busy = isParsing || isSaving

  return (
    <div className="hypothesis-section" ref={sectionRef}>
      {pending ? (
        <ParsedConfirm
          text={pending.text}
          parsed={pending.parsed}
          isSaving={isSaving}
          error={confirmError}
          onConfirm={handleConfirm}
          onBack={() => resetForm(draftText, editing, fromImprovement)}
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
          onUseSuggestion={(text) => resetForm(text, editing, fromImprovement)}
        />
      )}

      <h3 className="list-title">保存した仮説</h3>
      {(loadError || deleteError) && (
        <p className="form-error" role="alert">
          {loadError ?? deleteError}
        </p>
      )}
      <HypothesisList
        hypotheses={hypotheses}
        editingId={editing?.id ?? null}
        verifiedRun={verifiedRun}
        onUseImprovement={handleUseImprovement}
        disabled={busy || pending !== null}
        onEdit={(h) => resetForm(h.text, h)}
        onDelete={handleDelete}
      />
    </div>
  )
}
