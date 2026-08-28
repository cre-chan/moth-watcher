import unittest
from unittest.mock import Mock, patch

from app.alerts import AlertSender, GmailAlertSender, AlertSenderFactory


# AlertSender クラスの振る舞いを検証するユニットテスト
#  受信者アドレスが設定されている場合は SMTP でメール送信が行われること
#  受信者アドレスが空の場合は送信処理をスキップすること
class AlertSenderTests(unittest.TestCase):
    def test_send_sends_email_when_recipient_is_present(self):
        # 実際にメールを送信する設定を持つ AlertSender インスタンスを生成
        sender = AlertSender(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_address="watchmose@example.com",
            to_address="admin@example.com",
        )

        # smtplib.SMTP をモックに置き換え、実際の SMTP 通信を行わずに動作を検証
        with patch("app.alerts.smtplib.SMTP") as smtp_cls:
            smtp_instance = smtp_cls.return_value.__enter__.return_value

            sender.send("Emergency detected")

            # SMTP クライアントが正しいホスト・ポートで生成されることを確認
            smtp_cls.assert_called_once_with("smtp.example.com", 587)
            # TLS セッションの開始、認証、送信が順に呼び出されることを確認
            smtp_instance.starttls.assert_called_once_with()
            smtp_instance.login.assert_called_once_with("user", "pass")
            smtp_instance.send_message.assert_called_once()

            message = smtp_instance.send_message.call_args.args[0]
            self.assertEqual(message["Subject"], "Watchmose alert")
            self.assertEqual(message["From"], "watchmose@example.com")
            self.assertEqual(message["To"], "admin@example.com")
            self.assertIn("Emergency detected", message.get_content())

    def test_send_does_nothing_when_recipient_is_empty(self):
        # 受信者アドレスが空文字列の場合、送信処理をスキップすることを確認
        sender = AlertSender(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_address="watchmose@example.com",
            to_address="",
        )

        with patch("app.alerts.smtplib.SMTP") as smtp_cls:
            try:
                sender.send("Emergency detected")
                self.fail("Expected ValueError due to empty recipient address")
            except Exception as e:
                # SMTP クライアントが一度も生成されないことを確認
                smtp_cls.assert_not_called()

    @patch("app.alerts.build")
    def test_gmail_send_uses_gmail_api_and_encodes_message(self, build):
        # 単体テストでは認証情報とGmail APIをモックし、外部通信を行わない。
        credentials = Mock(valid=True, expired=False)
        sender = GmailAlertSender(credentials, None, "recipient@example.com")
        execute = build.return_value.users.return_value.messages.return_value.send.return_value.execute
        execute.return_value = {"id": "message-id"}

        result = sender.send("Moth detected", "Detection details")

        self.assertEqual(result, {"id": "message-id"})
        send = build.return_value.users.return_value.messages.return_value.send
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["userId"], "me")

if __name__ == "__main__":
    unittest.main()
