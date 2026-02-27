# Doc Shelf

`paper-shelf` をベースにした、汎用 PDF 向けの本棚アプリです。

- 論文専用機能は削除
- おすすめ論文 / 関連論文 / デイリーフィードなどの発見機能はなし
- PDF をアップロードして本棚（Shelf）で分類し、Web で閲覧・検索する用途に特化

## 主な機能

- PDF の複数ファイルアップロード
- 本棚（Shelf）の作成・削除・分類
- タイトル / 著者 / subject / タグ / 本文テキスト検索
- PDF インラインビュー
- 抽出テキストの表示
- CLI での追加・一覧・検索・本棚管理

## 構成

```
doc-shelf/
├── src/
│   ├── main.py                 # CLI エントリポイント
│   ├── pdf_extractor.py        # PDF テキスト抽出 (PyMuPDF)
│   ├── storage.py              # JSON / Markdown / Text / PDF 保存
│   ├── library.py              # index と shelf 管理
│   └── server/
│       ├── app.py              # FastAPI app
│       ├── routes_documents.py # ドキュメント API
│       ├── routes_shelves.py   # shelf API
│       ├── routes_upload.py    # upload + task API
│       └── tasks.py            # 非同期取り込みパイプライン
└── web/                        # React + TypeScript + Vite
```

## セットアップ

### 1. Python

```bash
pip install -e ".[dev]"
```

### 2. Frontend

```bash
cd web
npm install
npm run build
cd ..
```

`npm run build` で `src/server/static` にフロントエンドが出力されます。

## 起動

### Web UI

```bash
doc-shelf serve
# http://127.0.0.1:8000
```

### 開発モード

```bash
# Backend

doc-shelf serve --dev

# Frontend (別ターミナル)
cd web
npm run dev
```

## CLI 例

```bash
# PDF 追加
doc-shelf add ./sample.pdf

# shelf を指定して追加
doc-shelf add ./sample.pdf --shelf reports --shelf personal

# 一覧
doc-shelf list

# 検索（本文も含む）
doc-shelf search "meeting" --field all

# shelf 一覧
doc-shelf shelf list
```

## 保存先

デフォルトでは `library/` 配下に保存されます。

- `library/json/` : ドキュメントメタデータ
- `library/markdown/` : 人間向けプレビュー
- `library/texts/` : 抽出全文テキスト
- `library/pdfs/` : 元 PDF の保管
- `library/index.json` : 本棚とドキュメント索引
