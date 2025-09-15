"""SMTP mail sender CLI with SSL/STARTTLS, env credentials, and logging.

Usage examples:
  - Send a simple message (credentials from env MAIL_USERNAME/MAIL_PASSWORD):
    python mail_sender.py --server smtp.example.com --port 465 --ssl \
      --from you@example.com --to them@example.com \
      --subject "Hello" --text "Hi there!"

  - Read body from file:
    python mail_sender.py --server smtp.example.com --port 587 --starttls \
      --from you@example.com --to a@x.com b@y.com --subject "Report" \
      --text-file body.txt --username $USER --password $PASS
"""

from __future__ import annotations

import argparse
import logging
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class MailSendError(RuntimeError):
    """Raised when sending mail fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send an email via SMTP with SSL or STARTTLS.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--server", required=True, help="SMTP server hostname")
    parser.add_argument("--port", required=True, type=int, help="SMTP server port")
    auth = parser.add_argument_group("Authentication")
    auth.add_argument("--username", help="SMTP username; defaults to MAIL_USERNAME env")
    auth.add_argument("--password", help="SMTP password; defaults to MAIL_PASSWORD env")
    sec = parser.add_mutually_exclusive_group(required=True)
    sec.add_argument("--ssl", action="store_true", help="Use implicit SSL (SMTP_SSL)")
    sec.add_argument(
        "--starttls", action="store_true", help="Use STARTTLS after connect"
    )

    parser.add_argument(
        "--from", dest="from_addr", required=True, help="From email address"
    )
    parser.add_argument(
        "--to", nargs="+", required=True, help="Recipient email addresses"
    )
    parser.add_argument("--subject", default="(no subject)", help="Email subject")
    body = parser.add_mutually_exclusive_group(required=True)
    body.add_argument("--text", help="Plain text body")
    body.add_argument(
        "--text-file", type=Path, help="Path to a UTF-8 text file for body"
    )

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="SMTP timeout seconds"
    )
    return parser.parse_args()


def resolve_credentials(
    username_opt: Optional[str], password_opt: Optional[str]
) -> tuple[str, str]:
    username = username_opt or os.getenv("MAIL_USERNAME")
    password = password_opt or os.getenv("MAIL_PASSWORD")
    if not username or not password:
        raise MailSendError(
            "Missing credentials. Provide --username/--password or set MAIL_USERNAME/MAIL_PASSWORD env vars."
        )
    return username, password


def build_message(
    from_addr: str, to_addrs: List[str], subject: str, body_text: str
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.set_content(body_text)
    return msg


def read_body(text: Optional[str], text_file: Optional[Path]) -> str:
    if text is not None:
        return text
    assert text_file is not None
    try:
        return text_file.read_text(encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        raise MailSendError(f"Failed to read body file '{text_file}': {ex}") from ex


def send_mail(
    server: str,
    port: int,
    use_ssl: bool,
    use_starttls: bool,
    username: str,
    password: str,
    from_addr: str,
    to_addrs: List[str],
    message: EmailMessage,
    timeout: float,
) -> None:
    context = ssl.create_default_context()
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(
                server, port, context=context, timeout=timeout
            ) as smtp:
                smtp.login(username, password)
                smtp.send_message(message, from_addr=from_addr, to_addrs=to_addrs)
        else:
            with smtplib.SMTP(server, port, timeout=timeout) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message, from_addr=from_addr, to_addrs=to_addrs)
    except Exception as ex:  # noqa: BLE001
        raise MailSendError(f"SMTP error: {ex}") from ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        username, password = resolve_credentials(args.username, args.password)
        body_text = read_body(args.text, args.text_file)
        msg = build_message(args.from_addr, args.to, args.subject, body_text)
        send_mail(
            server=args.server,
            port=args.port,
            use_ssl=args.ssl,
            use_starttls=args.starttls,
            username=username,
            password=password,
            from_addr=args.from_addr,
            to_addrs=args.to,
            message=msg,
            timeout=args.timeout,
        )
    except MailSendError as ex:
        logger.error(str(ex))
        return 1

    logger.info(f"Sent email to {len(args.to)} recipient(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
