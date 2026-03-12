"""
Gestión de sesiones en Google Cloud Firestore con transacciones atómicas.

Implementa el patrón Human Handoff con timeout de 24 horas y control
de concurrencia optimista para evitar condiciones de carrera.
"""

from datetime import datetime, timezone, timedelta

from firebase_admin import firestore

from src.config import TIMEOUT_HOURS

db = firestore.client()


def check_and_update_session(wa_id: str) -> tuple[bool, str]:
    """Verifica el estado de la sesión y actualiza la marca temporal.

    Ejecuta una transacción atómica en Firestore para:
    1. Crear sesión nueva si no existe.
    2. Reactivar IA si el timeout de handoff humano expiró.
    3. Actualizar last_interaction.

    Args:
        wa_id: Número de WhatsApp del cliente.

    Returns:
        Tupla (ai_active, thread_id):
        - ai_active: True si la IA debe responder, False si hay humano activo.
        - thread_id: Identificador del hilo de conversación.
    """
    session_ref = db.collection("sessions").document(wa_id)
    now = datetime.now(timezone.utc)

    @firestore.transactional
    def execute_transaction(transaction, ref):
        snapshot = ref.get(transaction=transaction)

        if snapshot.exists:
            data = snapshot.to_dict()
            ai_active = data.get("ai_active", True)
            last_interaction = data.get("last_interaction", now)
            thread_id = data.get("thread_id", f"conv_{wa_id}")

            # Reactivar IA si el timeout de handoff humano expiró
            if not ai_active and (now - last_interaction) > timedelta(hours=TIMEOUT_HOURS):
                ai_active = True

            transaction.update(ref, {
                "last_interaction": now,
                "ai_active": ai_active,
            })
            return ai_active, thread_id
        else:
            # Nuevo prospecto: crear sesión con IA activa
            thread_id = f"conv_{wa_id}"
            transaction.set(ref, {
                "wa_id": wa_id,
                "thread_id": thread_id,
                "ai_active": True,
                "last_interaction": now,
            })
            return True, thread_id

    return execute_transaction(db.transaction(), session_ref)


def disable_ai_for_human(wa_id: str) -> None:
    """Desactiva la IA para permitir que un operador humano tome el control.

    Args:
        wa_id: Número de WhatsApp del cliente.
    """
    db.collection("sessions").document(wa_id).update({
        "ai_active": False,
    })
