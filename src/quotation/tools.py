"""
Panelin v5.0 - Agno Tool Wrappers
====================================

Wraps QuotationService methods as Agno tools so the conversational
agent can invoke them via function-calling.

Each tool is a standalone function decorated with type hints and docstrings
so Agno can auto-generate JSON schemas for the LLM.
"""

from __future__ import annotations

import json
from typing import Optional

from agno.tools import Toolkit

from src.quotation.service import QuotationService


class PanelinTools(Toolkit):
    """Agno toolkit exposing the Panelin v4 quotation engine."""

    def __init__(self):
        super().__init__(name="panelin_quotation")
        self.register(self.cotizar)
        self.register(self.buscar_precio)
        self.register(self.calcular_bom)
        self.register(self.validar_autoportancia)
        self.register(self.cotizacion_batch)

    def cotizar(
        self,
        texto: str,
        modo: str = "pre_cotizacion",
        nombre_cliente: Optional[str] = None,
        telefono_cliente: Optional[str] = None,
        ubicacion_cliente: Optional[str] = None,
    ) -> str:
        """Genera una cotización completa a partir de texto libre en español.

        El pipeline ejecuta: clasificar → parsear → SRE → BOM → pricing → validar.
        Devuelve el resultado completo incluyendo BOM, precios, validación y score SAI.

        Args:
            texto: Descripción del proyecto en español libre.
                   Ejemplo: "Isodec EPS 100mm / 6 paneles de 6.5mts / techo a metal"
            modo: Modo de operación: "informativo", "pre_cotizacion", o "formal".
            nombre_cliente: Nombre del cliente (opcional).
            telefono_cliente: Teléfono del cliente (opcional).
            ubicacion_cliente: Ubicación/dirección de obra (opcional).

        Returns:
            JSON con la cotización completa incluyendo quote_id, BOM, pricing, validación.
        """
        result = QuotationService.full_quotation(
            text=texto,
            mode=modo,
            client_name=nombre_cliente,
            client_phone=telefono_cliente,
            client_location=ubicacion_cliente,
        )
        sai = QuotationService.calculate_sai_score(result)
        result["sai"] = sai
        return json.dumps(result, ensure_ascii=False, indent=2)

    def buscar_precio(
        self,
        familia: str,
        sub_familia: str = "EPS",
        espesor_mm: int = 100,
    ) -> str:
        """Busca el precio de un panel en la base de conocimiento.

        Los precios provienen EXCLUSIVAMENTE de bromyros_pricing_master.json
        y accessories_catalog.json. NUNCA se inventan precios.

        Args:
            familia: Familia del producto (ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG).
            sub_familia: Sub-familia (EPS, PIR, 3G).
            espesor_mm: Espesor en milímetros.

        Returns:
            JSON con precio por m², fuente del precio, y disponibilidad.
        """
        from panelin_v4.engine.pricing_engine import _find_panel_price_m2

        price = _find_panel_price_m2(familia, sub_familia, espesor_mm)
        if price is not None:
            return json.dumps({
                "encontrado": True,
                "familia": familia,
                "sub_familia": sub_familia,
                "espesor_mm": espesor_mm,
                "precio_usd_m2": price,
                "iva_incluido": True,
                "fuente": "bromyros_pricing_master.json",
            }, ensure_ascii=False)
        return json.dumps({
            "encontrado": False,
            "familia": familia,
            "sub_familia": sub_familia,
            "espesor_mm": espesor_mm,
            "mensaje": f"Precio no encontrado para {familia} {sub_familia} {espesor_mm}mm en la KB",
        }, ensure_ascii=False)

    def calcular_bom(
        self,
        familia: str,
        sub_familia: str,
        espesor_mm: int,
        uso: str,
        largo_m: float,
        ancho_m: float,
        tipo_estructura: str = "metal",
        cantidad_paneles: Optional[int] = None,
        tipo_techo: Optional[str] = None,
        luz_m: Optional[float] = None,
    ) -> str:
        """Calcula el Bill of Materials (lista de materiales) para una instalación.

        Función determinística — CERO LLM. Calcula paneles, accesorios, fijaciones
        y selladores necesarios según las reglas del sistema constructivo.

        Args:
            familia: ISODEC, ISOROOF, ISOPANEL, ISOWALL, o ISOFRIG.
            sub_familia: EPS, PIR, o 3G.
            espesor_mm: Espesor del panel en mm (50, 80, 100, 150, 200).
            uso: Tipo de instalación: "techo", "pared", o "camara".
            largo_m: Largo del proyecto en metros.
            ancho_m: Ancho del proyecto en metros.
            tipo_estructura: "metal", "hormigon", o "madera".
            cantidad_paneles: Cantidad de paneles (si se conoce, override calculado).
            tipo_techo: Para techos: "1_agua", "2_aguas", "4_aguas", "mariposa".
            luz_m: Luz entre apoyos en metros (para validación de autoportancia).

        Returns:
            JSON con BOM completo: paneles, accesorios, cantidades, fórmulas.
        """
        result = QuotationService.calculate_bom(
            familia=familia,
            sub_familia=sub_familia,
            thickness_mm=espesor_mm,
            uso=uso,
            length_m=largo_m,
            width_m=ancho_m,
            structure_type=tipo_estructura,
            panel_count=cantidad_paneles,
            roof_type=tipo_techo,
            span_m=luz_m,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    def validar_autoportancia(
        self,
        familia: str,
        sub_familia: str,
        espesor_mm: int,
        luz_m: float,
    ) -> str:
        """Valida si un panel puede cubrir la luz solicitada sin apoyo intermedio.

        Consulta las tablas de autoportancia del fabricante y determina si
        el espesor elegido es suficiente. Si no, sugiere alternativas.

        Args:
            familia: Familia del producto.
            sub_familia: Sub-familia (EPS, PIR, 3G).
            espesor_mm: Espesor en mm.
            luz_m: Distancia entre apoyos en metros.

        Returns:
            JSON con estado (ok/warning/blocked), margen, y alternativas si aplica.
        """
        from panelin_v4.engine.sre_engine import _get_autoportancia, _find_valid_thicknesses

        luz_max = _get_autoportancia(familia, sub_familia, espesor_mm)
        if luz_max is None:
            return json.dumps({
                "status": "sin_datos",
                "mensaje": f"No hay tabla de autoportancia para {familia} {sub_familia} {espesor_mm}mm",
            }, ensure_ascii=False)

        ratio = luz_m / luz_max
        if ratio <= 0.85:
            status = "ok"
        elif ratio <= 1.0:
            status = "warning"
        else:
            status = "excedido"

        result = {
            "status": status,
            "familia": familia,
            "sub_familia": sub_familia,
            "espesor_mm": espesor_mm,
            "luz_solicitada_m": luz_m,
            "luz_maxima_m": luz_max,
            "margen_pct": round((1 - ratio) * 100, 1),
        }

        if status == "excedido":
            alternatives = _find_valid_thicknesses(familia, sub_familia, luz_m)
            result["alternativas_espesor_mm"] = alternatives
            result["recomendacion"] = (
                f"La luz de {luz_m}m excede el máximo de {luz_max}m. "
                f"Considere espesor: {alternatives[0]}mm" if alternatives
                else f"Agregue apoyo intermedio para reducir la luz a {luz_m/2:.1f}m"
            )

        return json.dumps(result, ensure_ascii=False, indent=2)

    def cotizacion_batch(
        self,
        solicitudes: str,
        modo: str = "pre_cotizacion",
    ) -> str:
        """Procesa múltiples cotizaciones en lote.

        Args:
            solicitudes: JSON string con lista de solicitudes.
                         Cada una debe tener al menos {"text": "..."}.
            modo: Modo de operación para todas las cotizaciones.

        Returns:
            JSON con lista de cotizaciones completas.
        """
        requests = json.loads(solicitudes)
        results = QuotationService.batch_quotation(requests, mode=modo)
        return json.dumps(results, ensure_ascii=False, indent=2)
