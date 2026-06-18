# Amazon クリエイティブ handoff ツール（Streamlit）

社内向け：商品情報 → 競合レビュー分析 → 構成/コピー → Codex handoff（固定プロンプト＋SP-API参考画像＋Dropbox/ZIP）。Python 3.12（uv 管理）。

## ローカル起動
1. `uv venv --python 3.12 && uv pip install -r requirements.txt`
2. `.streamlit/secrets.toml.example` を `.streamlit/secrets.toml` にコピーし値を設定
3. `.venv\Scripts\streamlit run app.py`

## テスト
`.venv\Scripts\pytest -q`

## 認証（Google ログイン / OIDC）
アクセス制御＝課金制御は **Google ログイン（`st.login`）＋ `APP_ALLOWED_USERS` の許可メール**で行う。
Community Cloud の無料枠は private アプリが1つだけのため、repo は **public**・アプリも public にし、
アプリ内の Google ログインで許可メールのみ通す方式。リポにシークレットは含めない（すべて `st.secrets`）。

## デプロイ（Streamlit Community Cloud・public + Google ログイン）
1. GitHub repo を **public** にする（コードのみ・シークレットは含まれない）。
2. Community Cloud で repo / branch `main` / `app.py` を指定、**Python 3.12**。
3. Google Cloud Console：OAuth 同意画面を作成 → 「Web アプリケーション」の OAuth クライアント ID を作成 →
   承認済みリダイレクト URI に `http://localhost:8501/oauth2callback` と
   `https://<デプロイURL>/oauth2callback` を登録 → client_id / client_secret を取得。
   テスト中は「テストユーザー」に許可メールを追加（or 公開）。
4. App settings > Secrets に登録：
   - `ANTHROPIC_API_KEY`
   - `APP_ALLOWED_USERS = ["...", ...]`（許可する Google メール）
   - `[auth]` セクション（`redirect_uri` は **デプロイURL**/oauth2callback、`cookie_secret` 強ランダム、`client_id`/`client_secret`、`server_metadata_url`）
   - SP-API（P3）：`SP_API_LWA_APP_ID` / `SP_API_LWA_CLIENT_SECRET` / `SP_API_REFRESH_TOKEN`
   - Dropbox（P3・任意）：`DROPBOX_APP_KEY` / `DROPBOX_APP_SECRET` / `DROPBOX_REFRESH_TOKEN` / `DROPBOX_BASE_PATH`
     （未設定なら handoff は ZIP ダウンロードのみ動作。設定すると共有フォルダへ直接アップロード）
5. 再デプロイ → 許可メールでログインできること、許可外メールが弾かれることを確認。
