# Life Transition

失恋後の30日間に、小さな経験を残すローカルMVP。Flask / SQLite / Pillow / FFmpeg。認証や外部サービスへの送信はありません。

## Macで起動

GitHubの「Code → Download ZIP」で取得して展開し、ターミナルで以下を実行します。Homebrewが必要です（https://brew.sh/ja/）。

```sh
brew install python ffmpeg
cd ~/Downloads/LifeTransitionApp-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Safariで `http://127.0.0.1:3000` を開きます。「デモを体験 → サンプルを入れる」で7日分を試せます。Your Storyから動画を生成・保存できます。終了はターミナルでControl+C。Mac標準の日本語フォントを自動検出します。見つからない場合は `LIFE_FONT` に日本語フォントの絶対パスを指定してください。

## クラウド環境で起動

Python 3.12、FFmpeg・ffprobe、Noto CJKフォントが必要です。このクラウド環境には導入済みです。

```sh
cd /workspace/LifeTransitionApp
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

ローカルのポート3000で起動します。クラウドのオンボーディングUIではローカルプレビューを提供しません。ご自身のPCで実行する場合はブラウザーでループバックのポート3000を開いてください。公開ネットワークにバインドしないでください。

## 操作

- Welcomeから開始日、タイトル、未来の自分への一言を設定。
- Todayで毎日異なる3段階の行動を選ぶ。選択変更・未完了の保存・休息も可能。
- 写真、1〜3秒の動画、一言、気分を任意で保存。My Journeyで振り返り・過去日の編集。
- 「デモを体験」→「サンプルを入れる」で7日分を用意。Dayを自由に切り替え、記録や動画生成を試せます。デモ削除は通常の記録に影響しません。
- Your Storyで7日間または30日間を指定してMP4生成。再生・ダウンロード・対応ブラウザーでファイル共有。
- SettingsからJourneyと記録を削除できます。

## 検証

```sh
.venv/bin/python -m unittest -v
.venv/bin/pip install -r requirements-dev.txt
# Chromiumが /usr/bin/chromium にあり、サーバー起動中の場合
.venv/bin/python test_browser.py
```

API統合テストは隔離した一時DBで作成、選択、完了、休息、画像・動画アップロード、不正ファイル拒否、デモ分離、MP4生成・デコード・ダウンロード、削除を検証。ブラウザーテストはデモデータを作成・編集・削除します（通常データは維持）。Pythonアプリなのでコンパイル用のビルド工程はありません。

## 現時点の制約

- 個人用ローカルアプリ。アカウント・アクセス制御・暗号化・クラウド同期は未実装。認証なしで一般公開しないこと。
- 動画は360×640、24fps、各カード2秒、フェード付き、音声なし。生成は同期処理。30日生成は対応していますが自動テストは7日生成を対象としています。
- Weekly Storyはボタンで生成。7日経過後の自動バックグラウンド生成は未実装。
- ミッションは各レベル10件のローテーション。少なくとも最初の7日は重複しません。30日を過ぎても記録可能（上限3650日）。
- カメラ・共有の挙動は端末依存。実機iPhoneでの検証は未実施。
- ファイルは25MBまで。画像を再エンコードし、動画はffprobe検証後に音声なしで再エンコード。保存先はdata/。本番向けのマルウェア検査・レート制限・バックアップは未実装。
- 単一ユーザー向け。Journey開始日の変更はDay番号に対応した記録の日付も変更します。

## 友達5〜10人で試す次のステップ

まず各自のPCで独立したデータを使い、同じチェックリストで操作と感想を集めてください。スマートフォンから配信して試す前に、ユーザー認証、利用者ごとのデータ分離、HTTPS、削除・同意・保存期間の方針、アップロード制限、非同期動画生成を実装してください。実機Safariでカメラ、動画再生、保存、共有も確認してください。
