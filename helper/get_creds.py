import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# メール送信に必要なスコープ
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

    flow = InstalledAppFlow.from_client_secrets_file(
        client_secret_path, SCOPES
    )
    # ラズパイなどヘッドレス環境（画面がない場合）は、
    # コンソールに表示されるURLを別のPCのブラウザにコピーして認証を完了させます
    creds = flow.run_local_server(port=0)

    # 次回のためにトークンを保存
    with open("token.json", "w") as token:
        token.write(creds.to_json())

    
