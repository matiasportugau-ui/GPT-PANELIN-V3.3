#!/usr/bin/env python3
"""
Panelin MCP Server - Wraps Wolf API for OpenAI MCP Integration
Handles authentication, validation, error handling, and response normalization
"""

import json
import os
from typing import Any, Dict, Optional
import requests
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PanelinMCPServer:
    """MCP-compliant wrapper for Panelin Wolf API"""

    def __init__(self, api_key: str, base_url: str = None):
        """
        Initialize MCP server

        Args:
            api_key: X-API-Key for Wolf API authentication
            base_url: Wolf API base URL (defaults to production)
        """
        self.api_key = api_key
        self.base_url = base_url or "https://panelin-api-642127786762.us-central1.run.app"
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })

    def tools_registry(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns MCP-compliant tool registry for OpenAI integration

        Returns:
            Dict with tool definitions including schemas
        """
        return {
            "find_products": {
                "type": "object",
                "name": "find_products",
                "description": "Search for construction panels using natural language",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                },
                "approval_required": False
            },
            "get_product_price": {
                "type": "object",
                "name": "get_product_price",
                "description": "Get current price for a specific product",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Product ID"
                        }
                    },
                    "required": ["product_id"]
                },
                "approval_required": False
            },
            "check_availability": {
                "type": "object",
                "name": "check_availability",
                "description": "Check product availability and delivery",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Product ID"
                        },
                        "quantity_needed": {
                            "type": "number",
                            "description": "Quantity needed (m²)"
                        }
                    },
                    "required": ["product_id", "quantity_needed"]
                },
                "approval_required": False
            },
            "calculate_quote": {
                "type": "object",
                "name": "calculate_quote",
                "description": "Generate quotation with pricing (REQUIRES APPROVAL)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "length_m": {"type": "number"},
                        "width_m": {"type": "number"},
                        "quantity": {"type": "integer", "default": 1},
                        "discount_percent": {"type": "number", "default": 0},
                        "include_accessories": {"type": "boolean", "default": True},
                        "include_tax": {"type": "boolean", "default": True},
                        "installation_type": {
                            "type": "string",
                            "enum": ["techo", "pared", "piso"]
                        }
                    },
                    "required": ["product_id", "length_m", "width_m", "installation_type"]
                },
                "approval_required": True
            },
            # Wolf API KB Write tools (v3.4)
            "persist_conversation": {
                "type": "object",
                "name": "persist_conversation",
                "description": "Save conversation summary to KB (REQUIRES APPROVAL)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string"},
                        "summary": {"type": "string"},
                        "quotation_ref": {"type": "string"},
                        "products_discussed": {"type": "array", "items": {"type": "string"}},
                        "password": {"type": "string"}
                    },
                    "required": ["client_id", "summary", "password"]
                },
                "approval_required": True
            },
            "register_correction": {
                "type": "object",
                "name": "register_correction",
                "description": "Register KB correction (REQUIRES APPROVAL)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_file": {"type": "string"},
                        "field_path": {"type": "string"},
                        "old_value": {"type": "string"},
                        "new_value": {"type": "string"},
                        "reason": {"type": "string"},
                        "reported_by": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "required": ["source_file", "field_path", "old_value", "new_value", "reason", "password"]
                },
                "approval_required": True
            },
            "save_customer": {
                "type": "object",
                "name": "save_customer",
                "description": "Store customer data for future quotations (REQUIRES APPROVAL)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "phone": {"type": "string"},
                        "address": {"type": "string"},
                        "city": {"type": "string"},
                        "department": {"type": "string"},
                        "notes": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "required": ["name", "phone", "password"]
                },
                "approval_required": True
            },
            "lookup_customer": {
                "type": "object",
                "name": "lookup_customer",
                "description": "Retrieve existing customer data from KB",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "search_query": {"type": "string"}
                    },
                    "required": ["search_query"]
                },
                "approval_required": False
            }
        }

    def find_products(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for products"""
        try:
            response = self.session.post(
                f"{self.base_url}/find_products",
                json={"query": query, "max_results": max_results},
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Product search successful: {query}")
            return {
                "success": True,
                "data": response.json(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Product search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def get_product_price(self, product_id: str) -> Dict[str, Any]:
        """Get current product price"""
        try:
            response = self.session.post(
                f"{self.base_url}/product_price",
                json={"product_id": product_id},
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Price lookup successful: {product_id}")
            return {
                "success": True,
                "data": response.json(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Price lookup failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def check_availability(self, product_id: str, quantity_needed: float) -> Dict[str, Any]:
        """Check product availability"""
        try:
            response = self.session.post(
                f"{self.base_url}/check_availability",
                json={"product_id": product_id, "quantity_needed": quantity_needed},
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Availability check successful: {product_id}")
            return {
                "success": True,
                "data": response.json(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Availability check failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def calculate_quote(
        self,
        product_id: str,
        length_m: float,
        width_m: float,
        quantity: int = 1,
        discount_percent: float = 0,
        include_accessories: bool = True,
        include_tax: bool = True,
        installation_type: str = "techo"
    ) -> Dict[str, Any]:
        """Calculate quotation (REQUIRES APPROVAL)"""
        try:
            payload = {
                "product_id": product_id,
                "length_m": length_m,
                "width_m": width_m,
                "quantity": quantity,
                "discount_percent": discount_percent,
                "include_accessories": include_accessories,
                "include_tax": include_tax,
                "installation_type": installation_type
            }
            response = self.session.post(
                f"{self.base_url}/calculate_quote",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Quotation calculation successful: {product_id}")
            return {
                "success": True,
                "data": response.json(),
                "timestamp": datetime.utcnow().isoformat(),
                "audit_info": {
                    "product_id": product_id,
                    "dimensions": f"{length_m}m × {width_m}m",
                    "quantity": quantity,
                    "discount": f"{discount_percent}%",
                    "installation_type": installation_type
                }
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Quotation calculation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    # --- Wolf API KB Write methods (v3.4) ---

    def persist_conversation(
        self,
        client_id: str,
        summary: str,
        quotation_ref: Optional[str] = None,
        products_discussed: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Save conversation summary to KB via POST /kb/conversations"""
        try:
            payload = {
                "client_id": client_id,
                "summary": summary,
                "quotation_ref": quotation_ref,
                "products_discussed": products_discussed or [],
                "date": datetime.utcnow().isoformat(),
            }
            response = self.session.post(
                f"{self.base_url}/kb/conversations",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Conversation persisted for client: {client_id}")
            return {"success": True, "data": response.json(), "timestamp": datetime.utcnow().isoformat()}
        except requests.exceptions.RequestException as e:
            logger.error(f"Persist conversation failed: {str(e)}")
            return {"success": False, "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def register_correction(
        self,
        source_file: str,
        field_path: str,
        old_value: str,
        new_value: str,
        reason: str,
        reported_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register KB correction via POST /kb/corrections"""
        try:
            payload = {
                "source_file": source_file,
                "field_path": field_path,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason,
                "reported_by": reported_by or "panelin_gpt",
                "date": datetime.utcnow().isoformat(),
            }
            response = self.session.post(
                f"{self.base_url}/kb/corrections",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Correction registered for {source_file}:{field_path}")
            return {"success": True, "data": response.json(), "timestamp": datetime.utcnow().isoformat()}
        except requests.exceptions.RequestException as e:
            logger.error(f"Register correction failed: {str(e)}")
            return {"success": False, "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def save_customer(
        self,
        name: str,
        phone: str,
        address: Optional[str] = None,
        city: Optional[str] = None,
        department: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store customer data via POST /kb/customers"""
        try:
            payload = {
                "name": name,
                "phone": phone,
                "address": address,
                "city": city,
                "department": department,
                "notes": notes,
                "last_interaction": datetime.utcnow().isoformat(),
            }
            response = self.session.post(
                f"{self.base_url}/kb/customers",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Customer saved: {name}")
            return {"success": True, "data": response.json(), "timestamp": datetime.utcnow().isoformat()}
        except requests.exceptions.RequestException as e:
            logger.error(f"Save customer failed: {str(e)}")
            return {"success": False, "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def lookup_customer(self, search_query: str) -> Dict[str, Any]:
        """Retrieve customer data via GET /kb/customers"""
        try:
            response = self.session.get(
                f"{self.base_url}/kb/customers",
                params={"search": search_query},
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Customer lookup successful: {search_query}")
            return {"success": True, "data": response.json(), "timestamp": datetime.utcnow().isoformat()}
        except requests.exceptions.RequestException as e:
            logger.error(f"Customer lookup failed: {str(e)}")
            return {"success": False, "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def health_check(self) -> Dict[str, bool]:
        """Check API health"""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return {"healthy": response.status_code == 200}
        except Exception:
            return {"healthy": False}
