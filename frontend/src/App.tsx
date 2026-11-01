import './App.css'

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>株式取引 仮説検証</h1>
      </header>
      <main className="app-main">
        {/* 左セクション：仮説の入力・一覧と、検証仮説の下に問題点（理由）・改善案 */}
        <section className="panel panel-left" aria-labelledby="left-title">
          <h2 id="left-title">仮説</h2>
          <p className="empty">まだ仮説がありません。</p>
        </section>
        {/* 右セクション：検証の条件と検証結果 */}
        <section className="panel panel-right" aria-labelledby="right-title">
          <h2 id="right-title">検証結果</h2>
          <p className="empty">仮説を選んで検証すると、ここに結果が表示されます。</p>
        </section>
      </main>
    </div>
  )
}

export default App
