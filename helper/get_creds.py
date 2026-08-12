"""Helper script for obtaining Gmail API credentials.

This module runs an OAuth2 authorization flow using a Google client secret
JSON file and saves the resulting credentials to a local token file.

Usage:
    python helper/get_creds.py <CLIENT_SECRET_PATH>

The generated credentials are written to token.json in the current working
directory, and can be reused by other Gmail API clients in the project.
"""

import os.path
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API 送信用の OAuth2 スコープ
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


if __name__ == "__main__":
    # プログラムの引数としてCLIENT_SECRET_PATHを受け取る
    # 受け取れなかった時に使い方を表示する
    if len(sys.argv) < 2:
        print("Usage: python get_creds.py <CLIENT_SECRET_PATH>")
        sys.exit(1)

    client_secret_path = sys.argv[1]
    if not os.path.exists(client_secret_path):
        print(f"Error: The file '{client_secret_path}' does not exist.")
        sys.exit(1)

    creds = None

    # Google OAuth2 フローを開始し、ブラウザで認証を促します
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_path, SCOPES
    )
    # ラズパイなどヘッドレス環境（画面がない場合）は、
    # コンソールに表示される URL を別の PC のブラウザにコピーして認証を完了させます
    creds = flow.run_local_server(port=0)

    # 取得した認証情報を JSON ファイルに保存します。
    with open("token.json", "w", encoding="utf-8") as token:
        token.write(creds.to_json())

    
