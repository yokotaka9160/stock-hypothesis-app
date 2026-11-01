import { useState } from 'react'
import type { Suggestion } from '../api/hypotheses'

const EXAMPLE_TEXT =
  '例：第1四半期の決算発表時刻を含む1時間足の、1本前の1時間足が確定したときに、その終値から4%上昇した価格で逆指値で買う。' +
  '市場前・市場後に買ったら市場前の最後の1時間足の終値で、市場中に買ったら市場中の最後の1時間足の終値で全部売る。'

interface Props {
  /** 編集するときの元の文章 */
  initialText?: string
  isEditing: boolean
  isParsing: boolean
  error: string | null
  /** 範囲外と判定されたときの、補った文章の提案（FR-026） */
  suggestion: Suggestion | null
  /** [保存] を押したとき。文章の読み取りを始める（FR-017） */
  onSubmit: (text: string) => void
  onCancelEdit: () => void
  /** 提案を入力欄に入れる。保存はしない */
  onUseSuggestion: (text: string) => void
}

/** 仮説の文章の入力欄（FR-001）。入力欄には例文を表示する */
export function HypothesisForm({
  initialText = '',
  isEditing,
  isParsing,
  error,
  suggestion,
  onSubmit,
  onCancelEdit,
  onUseSuggestion,
}: Props) {
  const [text, setText] = useState(initialText)

  return (
    <form
      className="hypothesis-form"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit(text)
      }}
    >
      <label htmlFor="hypothesis-text" className="form-label">
        {isEditing ? '仮説を編集' : '新しい仮説'}
      </label>
      <textarea
        id="hypothesis-text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={EXAMPLE_TEXT}
        rows={6}
        disabled={isParsing}
      />
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {suggestion && (
        <div className="suggestion">
          <p className="suggestion-title">検証できる範囲に合うように補った文章の提案</p>
          <p className="suggestion-text">{suggestion.text}</p>
          {suggestion.note && <p className="suggestion-note">補った内容：{suggestion.note}</p>}
          <button
            type="button"
            className="secondary"
            onClick={() => onUseSuggestion(suggestion.text)}
            disabled={isParsing}
          >
            この提案を入力欄に入れる
          </button>
        </div>
      )}
      <div className="form-actions">
        <button type="submit" disabled={isParsing || text.trim() === ''}>
          {isParsing ? '読み取り中…' : '保存'}
        </button>
        {isEditing && (
          <button type="button" className="secondary" onClick={onCancelEdit} disabled={isParsing}>
            編集をやめる
          </button>
        )}
      </div>
    </form>
  )
}
