from __future__ import annotations

import base64
import os
import smtplib
import time
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class AlertSender:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_address: str,
        to_address: str,
    ):
        # SMTP サーバー情報と認証情報、送信元/送信先アドレスを保持する
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.to_address = to_address

    def send(self, message: str) -> None:
        # 送信先アドレスが指定されていない場合は何もしない
        if not self.to_address:
            raise ValueError("No recipient address specified for alert email.")

        # EmailMessage を組み立てて件名・From/To を設定する
        msg = EmailMessage()
        msg["Subject"] = "Watchmose alert"
        msg["From"] = self.from_address
        msg["To"] = self.to_address
        msg.set_content(message)

        # SMTP セッションを開き、TLS を開始してログイン後にメッセージを送信する
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.send_message(msg)


class GmailAlertSender:
    """
    Gmail APIを使用してアラートメールを送信するクラス
    """

    DEFAULT_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    def __init__(
        self,
        credentials: Credentials,
        from_address: str | None,
        to_address: str,
        cooldown_seconds: float = 0,
    ):
        self.credentials = credentials
        self.from_address = from_address
        self.to_address = to_address
        self.cooldown_seconds = cooldown_seconds
        self.last_sent_at: float | None = None

    def _ensure_credentials(self) -> None:
        """
        Gmail APIの認証情報が有効であることを確認し、必要に応じてリフレッシュする。無効な場合はValueErrorをraiseする。  """
        if self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())

        if not self.credentials.valid:
            raise ValueError("Gmail credentials are invalid or could not be refreshed.")

    def _create_message(self, subject: str, body: str) -> dict[str, str]:
        msg = EmailMessage()
        msg["Subject"] = subject
        if self.from_address:
            msg["From"] = self.from_address
        msg["To"] = self.to_address
        msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return {"raw": raw}

    def send(self,subject: str, message: str) -> dict | None:
        if not self.to_address:
            raise ValueError("No recipient address specified for Gmail alert.")

        now = time.monotonic()
        # 通知モジュール内で、短時間に発生した重複メールを抑制する。
        if (
            self.last_sent_at is not None
            and now - self.last_sent_at < self.cooldown_seconds
        ):
            return None

        self._ensure_credentials()

        try:
            service = build("gmail", "v1", credentials=self.credentials)
            raw_message = self._create_message(subject, message)
            response = service.users().messages().send(userId="me", body=raw_message).execute()
            self.last_sent_at = now
            return response
        except HttpError as error:
            raise RuntimeError(f"Gmail API failed to send message: {error}") from error

class AlertSenderFactory:
    @staticmethod
    def create_gmail_sender_from_token(
        token_file: str,
        to_address: str,
        from_address: str | None = None,
        cooldown_seconds: float = 0,
    ) -> GmailAlertSender:
        """
        GmailAlertSenderをトークンファイルから作成するmethod. token_fileが存在しない場合はFileNotFoundErrorをraiseする.
        """
        # token_fileが存在しない場合はFileNotFoundErrorをraiseする
        if not os.path.exists(token_file):
            raise FileNotFoundError(f"Token file '{token_file}' does not exist. Try running get_creds.py to generate it.")

        # 与えられたtoken_fileからGmailの認証情報を読み込む
        credentials = Credentials.from_authorized_user_file(token_file, GmailAlertSender.DEFAULT_SCOPES)

        # 認証情報が有効ではない場合、refreshを試みる。refreshできない場合はValueErrorをraiseする
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                raise ValueError("Invalid or expired Gmail credentials. Please re-run get_creds.py to obtain new credentials.")

        # GmailAlertSenderを作成して返す
        return GmailAlertSender(
            credentials=credentials,
            from_address=from_address,
            to_address=to_address,
            cooldown_seconds=cooldown_seconds,
        )
