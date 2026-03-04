"""
Panelin v5.0 - Knowledge Base Persistence Tools
=================================================

Wraps Wolf API KB persistence endpoints as Agno tools.
Handles conversation persistence, customer data, and corrections.
"""

from __future__ import annotations

import json
from typing import Optional

from agno.tools import Toolkit


class KBPersistenceTools(Toolkit):
    """Agno toolkit for KB persistence operations via Wolf API."""

    def __init__(self, wolf_api_base_url: str = "http://localhost:8080", api_key: str = ""):
        super().__init__(name="panelin_kb")
        self._base_url = wolf_api_base_url.rstrip("/")
        self._api_key = api_key
        self.register(self.guardar_conversacion)
        self.register(self.guardar_cliente)
        self.register(self.buscar_cliente)

    async def _call_wolf(self, method: str, path: str, data: dict = None, params: dict = None) -> dict:
        import httpx
        headers = {"X-API-Key": self._api_key} if self._api_key else {}
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            resp.raise_for_status()
            return resp.json()

    def guardar_conversacion(
        self,
        resumen: str,
        cliente_id: str = "unknown",
        referencia_cotizacion: str = "",
        productos_discutidos: str = "[]",
    ) -> str:
        """Persiste un resumen de la conversación en la base de conocimiento.

        Args:
            resumen: Resumen de lo discutido en la conversación.
            cliente_id: Identificador del cliente.
            referencia_cotizacion: ID de cotización relacionada.
            productos_discutidos: JSON array de productos discutidos.

        Returns:
            JSON con confirmación de persistencia.
        """
        import asyncio

        async def _persist():
            products = json.loads(productos_discutidos) if productos_discutidos else []
            return await self._call_wolf("POST", "/kb/conversations", data={
                "client_id": cliente_id,
                "summary": resumen,
                "quotation_ref": referencia_cotizacion,
                "products_discussed": products,
            })

        try:
            result = asyncio.run(_persist())
        except RuntimeError:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _persist()).result()

        return json.dumps(result, ensure_ascii=False, indent=2)

    def guardar_cliente(
        self,
        nombre: str,
        telefono: str = "",
        direccion: str = "",
        ciudad: str = "",
        departamento: str = "",
        notas: str = "",
    ) -> str:
        """Guarda o actualiza datos de un cliente en la base de conocimiento.

        Args:
            nombre: Nombre completo del cliente.
            telefono: Número de teléfono.
            direccion: Dirección de obra o contacto.
            ciudad: Ciudad.
            departamento: Departamento de Uruguay.
            notas: Notas adicionales.

        Returns:
            JSON con customer_id asignado.
        """
        import asyncio

        async def _save():
            return await self._call_wolf("POST", "/kb/customers", data={
                "name": nombre,
                "phone": telefono,
                "address": direccion,
                "city": ciudad,
                "department": departamento,
                "notes": notas,
            })

        try:
            result = asyncio.run(_save())
        except RuntimeError:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _save()).result()

        return json.dumps(result, ensure_ascii=False, indent=2)

    def buscar_cliente(self, busqueda: str) -> str:
        """Busca un cliente existente por nombre, teléfono o ciudad.

        Args:
            busqueda: Texto de búsqueda (mínimo 2 caracteres).

        Returns:
            JSON con lista de clientes encontrados.
        """
        import asyncio

        async def _search():
            return await self._call_wolf("GET", "/kb/customers", params={"search": busqueda})

        try:
            result = asyncio.run(_search())
        except RuntimeError:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _search()).result()

        return json.dumps(result, ensure_ascii=False, indent=2)
