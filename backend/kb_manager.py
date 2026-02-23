import json
import os
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

logger = logging.getLogger(__name__)

class KBManager:
      """Manages knowledge base operations including CRUD and indexing."""

    def __init__(self, kb_root: str = "kb_pipeline"):
              self.kb_root = Path(kb_root)
              self.catalogs_dir = self.kb_root / "catalogs"
              self.artifacts_dir = Path("artifacts/hot")
              self.source_manifest = self.artifacts_dir / "source_manifest.json"

        # Ensure directories exist
              self.catalogs_dir.mkdir(parents=True, exist_ok=True)
              self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def validate_product(self, product: Dict) -> Tuple[bool, Optional[str]]:
              """Validate required fields in a product record."""
              required_fields = [
                  'sku', 'title', 'category', 'price', 
                  'availability', 'source_file', 'source_key'
              ]

        for field in required_fields:
                      if field not in product or not product[field]:
                                        return False, f"Missing required field: {field}"

                  try:
                                float(product['price'])
except (ValueError, TypeError):
              return False, f"Price must be numeric, got: {product['price']}"

        return True, None

    def load_catalog(self, catalog_name: str) -> Optional[List[Dict]]:
              """Load a catalog JSON file."""
              try:
                            catalog_path = self.catalogs_dir / f"{catalog_name}.json"
                            if not catalog_path.exists():
                                              logger.warning(f"Catalog {catalog_name} not found")
                                              return []

                            with open(catalog_path, 'r', encoding='utf-8') as f:
                                              data = json.load(f)
                                              return data if isinstance(data, list) else data.get('items', [])
              except Exception as e:
                            logger.error(f"Error loading catalog {catalog_name}: {e}")
                            return None

          def save_catalog(self, catalog_name: str, data: List[Dict]) -> bool:
                    """Save catalog to JSON file."""
                    try:
                                  catalog_path = self.catalogs_dir / f"{catalog_name}.json"
                                  with open(catalog_path, 'w', encoding='utf-8') as f:
                                                    json.dump(data, f, indent=2, ensure_ascii=False)
                                                logger.info(f"Catalog {catalog_name} saved")
                                  return True
except Exception as e:
            logger.error(f"Error saving catalog {catalog_name}: {e}")
            return False

    def add_or_update_product(
              self, 
              product: Dict, 
              catalog_name: str
    ) -> Tuple[bool, str]:
              """Add or update a product in the catalog."""
              is_valid, error = self.validate_product(product)
              if not is_valid:
                            return False, error

              catalog = self.load_catalog(catalog_name)
              if catalog is None:
                            return False, f"Failed to load catalog {catalog_name}"

              if 'checksum' not in product or product['checksum'] == 'auto':
                            product['checksum'] = self._generate_checksum(product)

              product['updated_at'] = datetime.now().isoformat()

        sku = product['sku']
        existing_idx = next(
                      (i for i, p in enumerate(catalog) if p.get('sku') == sku), 
                      None
        )

        if existing_idx is not None:
                      catalog[existing_idx].update(product)
                      action = "updated"
else:
              catalog.append(product)
              action = "added"

        if not self.save_catalog(catalog_name, catalog):
                      return False, f"Failed to save catalog {catalog_name}"

        return True, f"Product {sku} {action} successfully"

    def delete_product(self, sku: str, catalog_name: str) -> Tuple[bool, str]:
              """Delete a product from the catalog."""
              catalog = self.load_catalog(catalog_name)
              if catalog is None:
                            return False, f"Failed to load catalog {catalog_name}"

              original_len = len(catalog)
              catalog = [p for p in catalog if p.get('sku') != sku]

        if len(catalog) == original_len:
                      return False, f"Product {sku} not found in {catalog_name}"

        if not self.save_catalog(catalog_name, catalog):
                      return False, f"Failed to save catalog {catalog_name}"

        return True, f"Product {sku} deleted successfully"

    def search_products(
              self,
              query: str,
              category: Optional[str] = None,
              max_results: int = 10
    ) -> List[Dict]:
              """Search products across all catalogs."""
              results = []
              query_lower = query.lower()

        for catalog_file in self.catalogs_dir.glob("*.json"):
                      catalog_name = catalog_file.stem
                      catalog = self.load_catalog(catalog_name)

            if not catalog:
                              continue

            for product in catalog:
                              match = (
                                                    query_lower in str(product.get('sku', '')).lower() or
                                                    query_lower in str(product.get('title', '')).lower() or
                                                    query_lower in str(product.get('category', '')).lower()
                              )

                if not match:
                                      continue

                if category and product.get('category') != category:
                                      continue

                results.append(product)
                if len(results) >= max_results:
                                      return results

        return results

    def get_by_sku(self, sku: str) -> Optional[Dict]:
              """Get a single product by SKU."""
              results = self.search_products(sku, max_results=1)
              return results[0] if results else None

    def rebuild_indexes(self) -> Tuple[bool, str]:
              """Trigger the KB pipeline rebuild."""
              try:
                            result = subprocess.run(
                                              ['python', str(self.kb_root / 'build_indexes.py')],
                                              capture_output=True,
                                              text=True,
                                              timeout=60
                            )

            if result.returncode == 0:
                              logger.info("KB indexes rebuilt successfully")
                              return True, "KB rebuilt successfully"
else:
                  error = result.stderr or result.stdout
                  logger.error(f"KB rebuild failed: {error}")
                  return False, f"Rebuild failed: {error[:200]}"
except subprocess.TimeoutExpired:
            return False, "KB rebuild timed out (>60s)"
except Exception as e:
            logger.error(f"Error triggering rebuild: {e}")
            return False, str(e)

    def get_statistics(self) -> Dict:
              """Get KB statistics."""
              stats = {
                  'timestamp': datetime.now().isoformat(),
                  'catalogs': {}
              }

        for catalog_file in self.catalogs_dir.glob("*.json"):
                      catalog_name = catalog_file.stem
                      catalog = self.load_catalog(catalog_name)

            if catalog:
                              stats['catalogs'][catalog_name] = {
                                                    'total_products': len(catalog),
                                                    'categories': len(set(p.get('category') for p in catalog if p.get('category'))),
                                                    'last_modified': datetime.fromtimestamp(
                                                                              catalog_file.stat().st_mtime
                                                    ).isoformat()
                              }

        return stats

    @staticmethod
    def _generate_checksum(product: Dict) -> str:
              """Generate a checksum for a product."""
              key_fields = ['sku', 'title', 'price', 'availability']
              checksum_str = '|'.join(str(product.get(f, '')) for f in key_fields)
              return hashlib.md5(checksum_str.encode()).hexdigest()
