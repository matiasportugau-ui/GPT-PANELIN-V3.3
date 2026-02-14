#!/usr/bin/env python3
"""
Panelin + OpenAI MCP Integration
Full implementation for using Panelin Wolf API as OpenAI MCP tools via Responses API
"""

from openai import OpenAI
import json
import logging
from typing import Dict, Any, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PanelinMCPResponsesAPI:
    """Handle Panelin Wolf API via OpenAI Responses API with MCP tools"""

    def __init__(self, openai_api_key: str, wolf_api_key: str):
        """
        Initialize OpenAI + Panelin MCP integration

        Args:
            openai_api_key: OpenAI API key for GPT-5 access
            wolf_api_key: X-API-Key for Panelin Wolf API
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.wolf_api_key = wolf_api_key
        self.wolf_api_url = "https://panelin-api-642127786762.us-central1.run.app"

    def _get_mcp_tools_config(self):
        """Returns MCP tools configuration for Responses API"""
        return [{
            "type": "mcp",
            "server_label": "panelin_wolf",
            "server_url": self.wolf_api_url,
            "authorization": self.wolf_api_key,
            "require_approval": {
                "never": {
                    "tool_names": ["find_products", "get_product_price", "check_availability", "lookup_customer"]
                },
                "always": {
                    "tool_names": ["persist_conversation", "register_correction", "save_customer"]
                }
            }
        }]

    def search_products(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for products (auto-approved)"""
        logger.info(f"🔍 Searching products: {query}")

        resp = self.client.responses.create(
            model="gpt-4o",
            tools=self._get_mcp_tools_config(),
            input=f"""
                Search for construction panels matching this query: {query}
                Use the find_products function to search. Max results: {max_results}
            """
        )

        return {
            "query": query,
            "response_id": resp.id,
            "output": resp.output
        }

    def get_product_price(self, product_id: str) -> Dict[str, Any]:
        """Get product price (auto-approved)"""
        logger.info(f"💰 Getting price for: {product_id}")

        resp = self.client.responses.create(
            model="gpt-4o",
            tools=self._get_mcp_tools_config(),
            input=f"Get the current price for product ID: {product_id}"
        )

        return {
            "product_id": product_id,
            "response_id": resp.id,
            "output": resp.output
        }

    def check_availability(self, product_id: str, quantity_m2: float) -> Dict[str, Any]:
        """Check product availability (auto-approved)"""
        logger.info(f"📦 Checking availability: {product_id} ({quantity_m2}m²)")

        resp = self.client.responses.create(
            model="gpt-4o",
            tools=self._get_mcp_tools_config(),
            input=f"""
                Check availability for:
                - Product: {product_id}
                - Quantity needed: {quantity_m2} m²
                Use check_availability function
            """
        )

        return {
            "product_id": product_id,
            "quantity": quantity_m2,
            "response_id": resp.id,
            "output": resp.output
        }

    def create_quotation_with_approval(
        self,
        product_id: str,
        dimensions_m: Tuple[float, float],
        quantity: int = 1,
        discount_percent: float = 0,
        installation_type: str = "techo"
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Create quotation with approval workflow

        Returns: (resp1, approval_request, resp2_after_approval)
        """
        length_m, width_m = dimensions_m

        logger.info(f"📋 Step 1: Requesting quotation for {product_id}")
        print(f"\n{'='*60}")
        print(f"QUOTATION REQUEST")
        print(f"{'='*60}")
        print(f"Product: {product_id}")
        print(f"Dimensions: {length_m}m × {width_m}m")
        print(f"Quantity: {quantity}")
        print(f"Discount: {discount_percent}%")
        print(f"Installation: {installation_type}")

        # Step 1: Request quotation (may trigger approval request)
        resp1 = self.client.responses.create(
            model="gpt-4o",
            tools=self._get_mcp_tools_config(),
            input=f"""
                Generate a complete quotation with the following parameters:
                - Product ID: {product_id}
                - Length: {length_m}m
                - Width: {width_m}m
                - Quantity: {quantity}
                - Discount: {discount_percent}%
                - Installation type: {installation_type}
                - Include accessories: true
                - Include tax (IVA 22%): true

                Use the calculate_quote function to get the final pricing.
                Present the quotation details clearly.
            """
        )

        # Check for approval request
        approval_request = None
        for item in resp1.output:
            if hasattr(item, 'type') and item.type == "mcp_approval_request":
                approval_request = item
                logger.info(f"⏸️  Approval required for: {item.name}")
                print(f"\n⏸️  APPROVAL REQUIRED")
                print(f"Tool: {item.name}")
                print(f"Arguments: {item.arguments}")
                break

        if not approval_request:
            logger.info("✅ No approval needed - quotation generated")
            return resp1, None, None

        # Step 2: Get approval (simulated)
        print(f"\n❓ Awaiting salesperson approval...")
        user_input = input("Approve this quotation? (yes/no): ").lower()
        user_approved = user_input == "yes"

        # Step 3: Send approval response
        logger.info(f"📤 Sending approval response: {user_approved}")
        resp2 = self.client.responses.create(
            model="gpt-4o",
            tools=self._get_mcp_tools_config(),
            previous_response_id=resp1.id,
            input=[{
                "type": "mcp_approval_response",
                "approve": user_approved,
                "approval_request_id": approval_request.id
            }]
        )

        if user_approved:
            logger.info("✅ Quotation approved and generated!")
        else:
            logger.info("❌ Quotation rejected")

        return resp1, approval_request, resp2

    def extract_text_response(self, response_obj: Any) -> str:
        """Extract text from response output"""
        text_parts = []
        for item in response_obj.output:
            if hasattr(item, 'type') and item.type == "text":
                text_parts.append(item.text)
        return "\n".join(text_parts)


# Example usage
if __name__ == "__main__":
    import os

    openai_key = os.getenv("OPENAI_API_KEY")
    wolf_key = os.getenv("WOLF_API_KEY")

    if not openai_key or not wolf_key:
        print("⚠️  Please set OPENAI_API_KEY and WOLF_API_KEY environment variables")
        exit(1)

    # Initialize
    mcp_api = PanelinMCPResponsesAPI(openai_api_key=openai_key, wolf_api_key=wolf_key)

    # Example 1: Search products
    print("\n" + "="*60)
    print("EXAMPLE 1: Product Search (Auto-Approved)")
    print("="*60)
    search_result = mcp_api.search_products("panels para techos 100mm")
    text = mcp_api.extract_text_response(search_result)
    print(text[:500] + "..." if len(text) > 500 else text)

    # Example 2: Availability check
    print("\n" + "="*60)
    print("EXAMPLE 2: Availability Check (Auto-Approved)")
    print("="*60)
    stock_result = mcp_api.check_availability("ISODEC_EPS_100", quantity_m2=50)

    # Example 3: Quotation with approval (commented out for safety)
    # print("\n" + "="*60)
    # print("EXAMPLE 3: Quotation (Requires Approval)")
    # print("="*60)
    # resp1, approval_req, resp2 = mcp_api.create_quotation_with_approval(
    #     product_id="ISODEC_EPS_100",
    #     dimensions_m=(5.0, 11.0),
    #     discount_percent=5
    # )
