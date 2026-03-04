"""
Enrutador de inferencia con OpenAI Responses API.

Implementa la generación de respuestas con soporte para:
- RAG vía file_search (Vector Stores)
- Integración MCP para herramientas del CRM Inmoenter
- Detección de intención de escalado humano (Human Handoff)
"""

from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY, MCP_SERVER_URL, HANDOFF_KEYWORDS
from src.firestore_client import disable_ai_for_human


client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def generate_response(user_text: str, thread_id: str) -> str:
    """Genera una respuesta del agente cognitivo para el mensaje del usuario.

    Flujo:
    1. Detecta keywords de escalado humano → delega a operador.
    2. Invoca OpenAI Responses API con herramientas file_search + MCP.
    3. Retorna la respuesta generada.

    Args:
        user_text: Mensaje de texto del usuario.
        thread_id: Identificador del hilo de conversación (formato conv_{wa_id}).

    Returns:
        Respuesta de texto del agente (o mensaje de handoff).
    """
    # Detección inmediata de intención de escalado humano
    if any(word in user_text.lower() for word in HANDOFF_KEYWORDS):
        wa_id = thread_id.replace("conv_", "")
        disable_ai_for_human(wa_id)
        return "Comprendo. Un agente comercial revisará este chat a la brevedad."

    # Invocación de la Responses API con herramientas RAG + MCP
    response = await client.responses.create(
        model="gpt-4o",
        input=user_text,
        conversation={"id": thread_id},
        tools=[
            {"type": "file_search", "max_num_results": 3},
            {"type": "mcp", "server_url": MCP_SERVER_URL},
        ],
    )

    return response.output_text
