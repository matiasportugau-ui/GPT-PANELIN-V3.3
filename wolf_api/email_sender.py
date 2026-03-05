"""
email_sender.py — SMTP email endpoint for BMC Uruguay.

Sends emails from ventas@bmcuruguay.com.uy via SMTP.
Used by the Registrar Venta Apps Script to send pedidos a Bromyros.

Endpoint: POST /email/send_pedido

Add to main.py:
    from .email_sender import router as email_router
    app.include_router(email_router)

Environment variables (set in Cloud Run):
    SMTP_HOST=s111.nty.uy
    SMTP_PORT=465
    SMTP_USER=ventas@bmcuruguay.com.uy
    SMTP_PASS=<password>   ← Store in Secret Manager, NOT in code
"""

import os
import ssl
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger("panelin.email")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    expected = os.environ.get("WOLF_API_KEY", "")
    if not expected:
        raise HTTPException(503, "WOLF_API_KEY not configured")
    if not api_key or api_key != expected:
        raise HTTPException(401, "Invalid API Key")
    return api_key


# SMTP Configuration from environment
SMTP_CFG = {
    "host": os.environ.get("SMTP_HOST", "s111.nty.uy"),
    "port": int(os.environ.get("SMTP_PORT", "465")),
    "user": os.environ.get("SMTP_USER", "ventas@bmcuruguay.com.uy"),
    "password": os.environ.get("SMTP_PASS", ""),
    "from_name": os.environ.get("SMTP_FROM_NAME", "Matias Portugau"),
}


class EmailRequest(BaseModel):
    """Email request body."""
    to: str = Field(..., description="Destination email")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body (plain text)")
    cc: Optional[str] = Field(None, description="CC email (optional)")


router = APIRouter(tags=["Email"])


@router.post("/email/send_pedido")
async def send_pedido_email(
    req: EmailRequest,
    api_key: str = Security(verify_api_key),
):
    """
    Send a pedido email via SMTP from ventas@bmcuruguay.com.uy.

    Used by the Registrar Venta Apps Script when a sale is registered
    under proveedor BROMYROS.
    """
    if not SMTP_CFG["password"]:
        raise HTTPException(
            503,
            "SMTP_PASS not configured. Set it in Cloud Run environment variables."
        )

    try:
        # Build the email
        msg = MIMEMultipart()
        msg["From"] = f"{SMTP_CFG['from_name']} <{SMTP_CFG['user']}>"
        msg["To"] = req.to
        msg["Subject"] = req.subject
        if req.cc:
            msg["Cc"] = req.cc
        msg.attach(MIMEText(req.body, "plain", "utf-8"))

        # Send via SMTP SSL (port 465)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            SMTP_CFG["host"],
            SMTP_CFG["port"],
            context=context,
            timeout=30,
        ) as server:
            server.login(SMTP_CFG["user"], SMTP_CFG["password"])
            recipients = [req.to]
            if req.cc:
                recipients.append(req.cc)
            server.sendmail(
                SMTP_CFG["user"],
                recipients,
                msg.as_string(),
            )

        logger.info(f"Email sent to {req.to} — Subject: {req.subject}")
        return {
            "success": True,
            "message": f"Email sent to {req.to}",
            "from": SMTP_CFG["user"],
            "subject": req.subject,
        }

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP auth failed: {e}")
        raise HTTPException(401, f"SMTP authentication failed: {e}")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        raise HTTPException(502, f"SMTP error: {e}")
    except Exception as e:
        logger.error(f"Email send failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to send email: {e}")


@router.get("/email/health")
async def email_health():
    """Check if SMTP is configured."""
    return {
        "smtp_host": SMTP_CFG["host"],
        "smtp_port": SMTP_CFG["port"],
        "smtp_user": SMTP_CFG["user"],
        "smtp_pass_configured": bool(SMTP_CFG["password"]),
    }
