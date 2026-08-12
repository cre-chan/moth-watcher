from __future__ import annotations

import base64
import os
import smtplib
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
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
    ):
        self.credentials = credentials
        self.from_address = from_address
        self.to_address = to_address

    @classmethod
    def from_client_secrets_file(
        cls,
        client_secrets_file: str,
        token_file: str,
        to_address: str,
        from_address: str | None = None,
        scopes: list[str] | None = None,
    ) -> "GmailAlertSender":
        scopes = scopes or cls.DEFAULT_SCOPES
        credentials: Credentials | None = None

        if os.path.exists(token_file):
            credentials = Credentials.from_authorized_user_file(token_file, scopes)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
                credentials = flow.run_local_server(port=0)

            with open(token_file, "w", encoding="utf-8") as token:
                token.write(credentials.to_json())

        return cls(credentials=credentials, from_address=from_address, to_address=to_address)

    def _ensure_credentials(self) -> None:
        if not self.credentials:
            raise ValueError("Credentials must be provided for GmailAlertSender.")

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

    def send(self, message: str) -> dict:
        if not self.to_address:
            raise ValueError("No recipient address specified for Gmail alert.")

        self._ensure_credentials()

        try:
            service = build("gmail", "v1", credentials=self.credentials)
            raw_message = self._create_message("Watchmose alert", message)
            return service.users().messages().send(userId="me", body=raw_message).execute()
        except HttpError as error:
            raise RuntimeError(f"Gmail API failed to send message: {error}") from error
