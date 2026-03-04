"""
Capa de transporte hacia WhatsApp Cloud API (Meta Graph API v18.0).

Implementa el envío asíncrono de mensajes de texto y documentos PDF
utilizando httpx AsyncClient para máximo rendimiento en Cloud Run.
"""

import httpx

from src.config import WHATSAPP_TOKEN, WHATSAPP_API_BASE


async def send_whatsapp_message(to: str, text: str) -> None:
    """Envía un mensaje de texto vía WhatsApp Cloud API.

    Args:
        to: Número de teléfono del destinatario.
        text: Contenido del mensaje de texto.
    """
    url = f"{WHATSAPP_API_BASE}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)


async def send_whatsapp_pdf(to: str, filepath: str, filename: str) -> None:
    """Envía un documento PDF vía WhatsApp Cloud API (flujo de 2 fases).

    Fase 1: Upload del archivo a Meta (obtención del media_id).
    Fase 2: Envío del mensaje con referencia al media_id.

    IMPORTANTE: El archivo se envía como tupla estructurada en multipart/form-data
    para evitar el error OAuthException Code 100 de Meta.

    Args:
        to: Número de teléfono del destinatario.
        filepath: Ruta al archivo PDF en disco.
        filename: Nombre del archivo que verá el usuario.
    """
    upload_url = f"{WHATSAPP_API_BASE}/media"
    headers_upload = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    async with httpx.AsyncClient() as client:
        # Fase 1: Upload (estructura de tupla OBLIGATORIA para multipart/form-data)
        with open(filepath, "rb") as f:
            files = {"file": (filename, f, "application/pdf")}
            data = {"messaging_product": "whatsapp", "type": "application/pdf"}
            upload_resp = await client.post(
                upload_url, headers=headers_upload, data=data, files=files
            )

        if upload_resp.status_code == 200:
            media_id = upload_resp.json().get("id")

            # Fase 2: Envío del mensaje referenciando el media_id
            msg_url = f"{WHATSAPP_API_BASE}/messages"
            headers_msg = {
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "document",
                "document": {
                    "id": media_id,
                    "filename": filename,
                    "caption": "Documento adjunto.",
                },
            }
            await client.post(msg_url, headers=headers_msg, json=payload)
