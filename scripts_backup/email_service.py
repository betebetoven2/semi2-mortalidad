from __future__ import annotations

import os
import ssl
import smtplib
import traceback
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from typing import Optional, Sequence, Dict, Any


@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    from_name: str
    recipients: Sequence[str]


class EmailNotifier:
    """
    Servicio de notificación por correo para el cronjob de backups
    de la Plataforma Analítica de Mortalidad End-to-End.

    No lee secretos por defecto: si SMTP_USER/SMTP_PASS/EMAIL_TO
    no están en el .env, lanza un error en lugar de usar un valor
    hardcodeado.
    """

    def __init__(self, *, config: Optional[EmailConfig] = None) -> None:
        self._config = config or self._load_config()

    def send_error(self, error_title: str, error_details: Optional[str] = None,
                    *, context: Optional[Dict[str, Any]] = None) -> bool:
        timestamp = self._now_str()
        subject = self._safe_subject(prefix="⚠️ Backup DW - Error", title=error_title)
        plain = self._build_error_plain(timestamp, error_title, error_details, context)
        html = self._build_error_html(timestamp, error_title, error_details, context)
        return self._send_to_all(subject=subject, plain=plain, html=html)

    def send_success(self, success_title: str, *, summary: Optional[Dict[str, Any]] = None) -> bool:
        timestamp = self._now_str()
        subject = self._safe_subject(prefix="✅ Backup DW - OK", title=success_title)
        plain = self._build_success_plain(timestamp, success_title, summary)
        html = self._build_success_html(timestamp, success_title, summary)
        return self._send_to_all(subject=subject, plain=plain, html=html)

    def _load_config(self) -> EmailConfig:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "465"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        from_name = os.getenv("EMAIL_FROM_NAME", "Mortalidad GTM - Backup DW")
        recipients_env = os.getenv("EMAIL_TO", "").strip()
        recipients = [e.strip() for e in recipients_env.split(",") if e.strip()]

        if not smtp_user or not smtp_pass:
            raise ValueError("Faltan SMTP_USER / SMTP_PASS en el .env")
        if not recipients:
            raise ValueError("Falta EMAIL_TO en el .env")

        return EmailConfig(smtp_host, smtp_port, smtp_user, smtp_pass, from_name, tuple(recipients))

    def _send_to_all(self, *, subject: str, plain: str, html: str) -> bool:
        ok_all = True
        for r in self._config.recipients:
            ok_all = self._send_one(recipient=r, subject=subject, plain=plain, html=html) and ok_all
        return ok_all

    def _send_one(self, *, recipient: str, subject: str, plain: str, html: str) -> bool:
        msg = EmailMessage()
        msg["From"] = f"{self._config.from_name} <{self._config.smtp_user}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(plain)
        msg.add_alternative(html, subtype="html")
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(self._config.smtp_host, self._config.smtp_port, context=ctx) as server:
                server.login(self._config.smtp_user, self._config.smtp_pass.replace(" ", ""))
                server.send_message(msg)
            print(f"[EmailNotifier] Enviado: '{subject}' -> {recipient}")
            return True
        except Exception as exc:
            print(f"[EmailNotifier] FALLO enviando a {recipient}: {exc!r}")
            traceback.print_exc()
            return False

    @staticmethod
    def _now_str() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _safe_subject(*, prefix: str, title: str, max_len: int = 90) -> str:
        clean = " ".join((title or "").split()).strip()
        if len(clean) > 60:
            clean = clean[:60].rstrip() + "…"
        return f"{prefix}: {clean}"[:max_len].rstrip()

    def _build_error_plain(self, ts, title, details, context):
        ctx = self._format_context_plain(context)
        d = details or "Sin detalles adicionales."
        return (f"Plataforma Analitica de Mortalidad - Alerta de Backup\n\n"
                f"Hora: {ts}\n\nError: {title}\n\n{ctx}Detalles:\n{d}\n")

    def _build_success_plain(self, ts, title, summary):
        s = self._format_context_plain(summary, header="Resumen")
        return (f"Plataforma Analitica de Mortalidad - Backup DW\n\n"
                f"Hora: {ts}\n\n{title}\n\n{s}")

    @staticmethod
    def _format_context_plain(ctx, header="Contexto"):
        if not ctx:
            return ""
        lines = [f"{header}:"] + [f"- {k}: {v}" for k, v in ctx.items()]
        return "\n".join(lines) + "\n\n"

    def _build_error_html(self, ts, title, details, context):
        ctx_html = self._format_context_html(context)
        det_html = (f'<div class="box"><b>Detalles:</b><pre>{self._esc(details)}</pre></div>' if details else "")
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
        body{{font-family:Arial,sans-serif;background:#f4f4f4;padding:20px}}
        .container{{background:#fff;border-radius:10px;max-width:650px;margin:0 auto;overflow:hidden}}
        .header{{background:#c0392b;color:#fff;padding:20px;text-align:center}}
        .content{{padding:20px}} .box{{background:#fdecea;border-left:4px solid #c0392b;padding:12px;border-radius:6px;margin:10px 0}}
        pre{{white-space:pre-wrap;font-size:12px}} .footer{{background:#fafafa;padding:14px;text-align:center;color:#888;font-size:12px}}
        </style></head><body><div class="container">
        <div class="header"><h2>⚠️ Backup DW - Error</h2></div>
        <div class="content"><p><b>Hora:</b> {ts}</p><div class="box"><b>{self._esc(title)}</b></div>
        {ctx_html}{det_html}</div>
        <div class="footer">{self._esc(self._config.from_name)} · notificación automática</div>
        </div></body></html>"""

    def _build_success_html(self, ts, title, summary):
        s_html = self._format_context_html(summary, header="Resumen")
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
        body{{font-family:Arial,sans-serif;background:#f4f4f4;padding:20px}}
        .container{{background:#fff;border-radius:10px;max-width:650px;margin:0 auto;overflow:hidden}}
        .header{{background:#27ae60;color:#fff;padding:20px;text-align:center}}
        .content{{padding:20px}} .box{{background:#eafaf1;border-left:4px solid #27ae60;padding:12px;border-radius:6px;margin:10px 0}}
        .footer{{background:#fafafa;padding:14px;text-align:center;color:#888;font-size:12px}}
        </style></head><body><div class="container">
        <div class="header"><h2>✅ Backup DW Exitoso</h2></div>
        <div class="content"><p><b>Hora:</b> {ts}</p><div class="box">{self._esc(title)}</div>{s_html}</div>
        <div class="footer">{self._esc(self._config.from_name)} · notificación automática</div>
        </div></body></html>"""

    @staticmethod
    def _format_context_html(ctx, header="Contexto"):
        if not ctx:
            return ""
        items = "".join(f"<li><b>{EmailNotifier._esc(str(k))}:</b> {EmailNotifier._esc(str(v))}</li>" for k, v in ctx.items())
        return f'<div><h4>{header}</h4><ul>{items}</ul></div>'

    @staticmethod
    def _esc(v):
        if v is None:
            return ""
        return (str(v).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
