from __future__ import annotations

import smtplib
from email.message import EmailMessage


class AlertSender:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, from_address: str, to_address: str):
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
            return

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
