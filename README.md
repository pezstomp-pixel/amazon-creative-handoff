# Amazon クリエイティブ handoff ツール（Streamlit）

社内向け：商品情報 → 競合レビュー分析 →（P2以降）構成/コピー → Codex handoff。Python 3.12（uv 管理）。

## ローカル起動
1. `uv venv --python 3.12 && uv pip install -r requirements.txt`
2. `.streamlit/secrets.toml.example` を `.streamlit/secrets.toml` にコピーし値を設定
3. `.venv\Scripts\streamlit run app.py`

## テスト
`.venv\Scripts\pytest -q`

## デプロイ（Streamlit Community Cloud）
- GitHub repo `amazon-creative-handoff` を private で連携
- アプリを **private**＋ビュワー許可メールに設定（課金制御）
- Python バージョンは **3.12** を指定
- App settings > Secrets に secrets.toml の値を登録
