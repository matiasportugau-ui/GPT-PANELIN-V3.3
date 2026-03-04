"""
Panelin v5.0 - Google Sheets Integration Tools
================================================

Wraps the Wolf API Google Sheets endpoints as Agno tools so the
agent can read/write the CRM spreadsheet directly.
"""

from __future__ import annotations

import json
from typing import Optional

from agno.tools import Toolkit


class SheetsTools(Toolkit):
    """Agno toolkit for Google Sheets CRM operations."""

    def __init__(self, wolf_api_base_url: str = "http://localhost:8080", api_key: str = ""):
        super().__init__(name="panelin_sheets")
        self._base_url = wolf_api_base_url.rstrip("/")
        self._api_key = api_key
        self.register(self.buscar_cliente_sheets)
        self.register(self.agregar_consulta)
        self.register(self.registrar_cotizacion)
        self.register(self.estadisticas_sheets)

    async def _call_wolf(self, method: str, path: str, data: dict = None, params: dict = None) -> dict:
        import httpx
        headers = {"X-API-Key": self._api_key} if self._api_key else {}
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=data)
            elif method == "PATCH":
                resp = await client.patch(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            resp.raise_for_status()
            return resp.json()

    def buscar_cliente_sheets(self, consulta: str, limite: int = 20) -> str:
        """Busca un cliente en la planilla de Google Sheets del CRM.

        Args:
            consulta: Texto a buscar (nombre, teléfono, consulta).
            limite: Máximo de resultados a devolver.

        Returns:
            JSON con los resultados encontrados.
        """
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        async def _search():
            return await self._call_wolf("GET", "/sheets/search", params={"q": consulta, "limit": limite})

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _search()).result()
        else:
            result = asyncio.run(_search())

        return json.dumps(result, ensure_ascii=False, indent=2)

    def agregar_consulta(
        self,
        cliente: str,
        consulta: str,
        telefono: str = "",
        direccion: str = "",
        origen: str = "PANELIN",
        asignado: str = "",
    ) -> str:
        """Agrega una nueva consulta a la planilla de Google Sheets.

        Args:
            cliente: Nombre del cliente.
            consulta: Descripción de la consulta/proyecto.
            telefono: Teléfono del cliente.
            direccion: Dirección de obra.
            origen: Origen de la consulta (PANELIN, WEB, TEL, etc.).
            asignado: Vendedor asignado.

        Returns:
            JSON con confirmación y número de fila.
        """
        import asyncio

        async def _add():
            return await self._call_wolf("POST", "/sheets/consultations", data={
                "cliente": cliente,
                "consulta": consulta,
                "telefono": telefono,
                "direccion": direccion,
                "origen": origen,
                "asignado": asignado,
            })

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _add()).result()
        else:
            result = asyncio.run(_add())

        return json.dumps(result, ensure_ascii=False, indent=2)

    def registrar_cotizacion(
        self,
        fila: int,
        estado: str = "Enviado",
        comentarios: str = "",
    ) -> str:
        """Registra una cotización enviada en la planilla (actualiza fila existente).

        Args:
            fila: Número de fila en la planilla.
            estado: Estado de la consulta (Enviado, Cerrado, etc.).
            comentarios: Comentarios adicionales sobre la cotización.

        Returns:
            JSON con confirmación.
        """
        import asyncio

        async def _update():
            return await self._call_wolf("POST", "/sheets/quotation_line", data={
                "row_number": fila,
                "estado": estado,
                "comentarios": comentarios,
            })

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _update()).result()
        else:
            result = asyncio.run(_update())

        return json.dumps(result, ensure_ascii=False, indent=2)

    def estadisticas_sheets(self) -> str:
        """Obtiene estadísticas del CRM (total consultas, por estado, por origen).

        Returns:
            JSON con estadísticas agregadas.
        """
        import asyncio

        async def _stats():
            return await self._call_wolf("GET", "/sheets/stats")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _stats()).result()
        else:
            result = asyncio.run(_stats())

        return json.dumps(result, ensure_ascii=False, indent=2)
