"""
Panelin Agent V3.1 - Enhanced Quotation Calculator with Autoportancia Validation
===============================================================================

VERSION: 3.1 (Autoportancia Validation)
DATE: 2026-02-07

CRITICAL ARCHITECTURE PRINCIPLE:
- The LLM NEVER performs arithmetic calculations
- All mathematical operations use Python's Decimal for financial precision
- Every calculation is deterministic and verifiable
- Results include 'calculation_verified: True' flag to ensure LLM didn't calculate

NEW IN V3.1:
- Autoportancia (span/load) validation against exact manufacturer nominal limits (no safety margin)
- Validates 4 product families, ~15 thickness configurations
- Intelligent recommendations when limits exceeded
- Optional validation parameter (non-breaking enhancement)

NEW IN V3.0:
- Full accessories catalog integration (97 items with real prices)
- BOM system selection (6 construction systems)
- Accessories valorization (replaces TODO at line 450)
- Enhanced AccessoriesResult with line_items and pricing

This module implements all quotation calculations for BMC Uruguay panel products.
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from typing import TypedDict, Optional, List, Literal
from pathlib import Path
import json
import math
import threading

# Optimization constants
OPTIMIZATION_STEP_M = 0.05  # 5cm steps for length optimization
BINARY_SEARCH_MIN_RANGE_M = 0.5  # Minimum range (10 steps) to use binary search over linear

# Type definitions for structured outputs
class ProductSpecs(TypedDict):
    product_id: str
    name: str
    family: str
    sub_family: str
    thickness_mm: int
    price_per_m2: float
    currency: str
    ancho_util_m: float
    largo_min_m: float
    largo_max_m: float
    autoportancia_m: float
    stock_status: str


class AccessoriesResult(TypedDict):
    panels_needed: int
    supports_needed: int
    fixation_points: int
    rod_quantity: int
    front_drip_edge_units: int
    lateral_drip_edge_units: int
    rivets_needed: int
    silicone_tubes: int
    metal_nuts: int
    concrete_nuts: int
    concrete_anchors: int
    # V3 ENHANCEMENTS: Pricing fields
    line_items: List['QuotationLineItem']  # Detailed accessory line items with prices
    accessories_subtotal_usd: float  # Sum of all accessory prices


class LineItemTrace(TypedDict, total=False):
    """Traceability: which rule produced this line item and how."""
    rule_id: str
    formula: str
    source_file: str


class QuotationLineItem(TypedDict):
    product_id: str
    name: str
    quantity: int
    area_m2: float
    unit_price_usd: float
    line_total_usd: float
    trace: Optional[LineItemTrace]


class AutoportanciaValidationResult(TypedDict):
    """Result of autoportancia (span/load) validation"""
    is_valid: bool
    span_requested_m: float
    span_max_m: float
    span_max_safe_m: float  # With safety margin applied
    excess_pct: float  # Percentage over safe limit (if exceeded)
    recommendation: str
    alternative_thicknesses: List[int]  # Suggested thicknesses that would work


class QuotationResult(TypedDict):
    """Complete quotation result with deterministic calculations"""
    quotation_id: str
    product_id: str
    product_name: str
    
    # Dimensions
    length_m: float  # Requested length
    actual_length_m: float  # Actual panel length delivered
    width_m: float
    area_m2: float
    
    # Panel calculations
    panels_needed: int
    unit_price_per_m2: float
    
    # Pricing
    subtotal_usd: float
    discount_percent: float
    discount_amount_usd: float
    total_before_tax_usd: float
    tax_amount_usd: float
    total_usd: float
    
    # Accessories (optional)
    accessories: Optional[AccessoriesResult]
    accessories_total_usd: float
    
    # Grand total
    grand_total_usd: float
    
    # Autoportancia validation (optional)
    autoportancia_validation: Optional[AutoportanciaValidationResult]
    
    # Verification flag - CRITICAL: must always be True
    calculation_verified: bool
    calculation_method: str
    currency: str
    notes: List[str]  # Notes including cutting instructions

    # V3.2 Traceability: maps each line item back to its rule
    trace_log: Optional[List[dict]]


def _load_knowledge_base() -> dict:
    """Load the single source of truth knowledge base with caching.
    
    Thread-safe using double-checked locking pattern.
    """
    global _KNOWLEDGE_BASE_CACHE
    
    # Fast path: check if already initialized (no lock needed for read)
    if _KNOWLEDGE_BASE_CACHE is not None:
        return _KNOWLEDGE_BASE_CACHE
    
    # Slow path: need to load KB with lock
    with _kb_cache_lock:
        # Double-check inside lock (another thread may have loaded it)
        if _KNOWLEDGE_BASE_CACHE is not None:
            return _KNOWLEDGE_BASE_CACHE
        
        # Try config directory first
        kb_path = Path(__file__).parent.parent / "config" / "panelin_truth_bmcuruguay.json"
        
        if not kb_path.exists():
            # Try root directory with version suffix
            kb_path = Path(__file__).parent / "panelin_truth_bmcuruguay_web_only_v2.json"
        
        if not kb_path.exists():
            raise FileNotFoundError(f"Knowledge base not found at {kb_path}")
        
        with open(kb_path, 'r', encoding='utf-8') as f:
            _KNOWLEDGE_BASE_CACHE = json.load(f)
        
        return _KNOWLEDGE_BASE_CACHE


# V3 ENHANCEMENT: Catalog caching
_ACCESSORIES_CATALOG_CACHE = None
_BOM_RULES_CACHE = None
_KNOWLEDGE_BASE_CACHE = None
_PRODUCT_INDEX_CACHE = None  # Index for fast product lookups
_kb_cache_lock = threading.Lock()
_product_index_lock = threading.Lock()


def _build_product_index(products: dict) -> dict:
    """Build indices for fast product lookups by family+thickness+application.
    
    Returns dict with:
        - by_family_thickness: {(family_upper, thickness_mm): [product_ids]}
        - normalized_applications: {product_id: [normalized_apps]}
    """
    by_family_thickness = {}
    normalized_applications = {}
    
    for pid, p in products.items():
        family = p.get("family", "").upper()
        thickness = p.get("thickness_mm")
        
        # Index by (family, thickness)
        if family and thickness is not None:
            key = (family, thickness)
            if key not in by_family_thickness:
                by_family_thickness[key] = []
            by_family_thickness[key].append(pid)
        
        # Pre-normalize applications for faster search
        apps = p.get("application", [])
        normalized_applications[pid] = [a.lower() for a in apps] if apps else []
    
    return {
        "by_family_thickness": by_family_thickness,
        "normalized_applications": normalized_applications
    }


def _load_accessories_catalog() -> dict:
    """
    Load accessories catalog with 97 items and pricing.
    
    V3 NEW: Loads from organized KB structure with caching.
    
    Returns:
        dict: Catalog with 'accesorios' array and 'indices' for fast lookup
    """
    global _ACCESSORIES_CATALOG_CACHE
    if _ACCESSORIES_CATALOG_CACHE is not None:
        return _ACCESSORIES_CATALOG_CACHE
    
    # Try organized KB structure first, then fall back to root
    catalog_path = Path(__file__).parent.parent / "01_KNOWLEDGE_BASE" / "Level_1_2_Accessories" / "accessories_catalog.json"
    
    if not catalog_path.exists():
        # Fallback to root directory
        catalog_path = Path(__file__).parent / "accessories_catalog.json"
    
    if not catalog_path.exists():
        raise FileNotFoundError(f"Accessories catalog not found at {catalog_path}")
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        _ACCESSORIES_CATALOG_CACHE = json.load(f)
    
    return _ACCESSORIES_CATALOG_CACHE


def _load_bom_rules() -> dict:
    """
    Load BOM rules for 6 construction systems.
    
    V3 NEW: Loads parametric rules and autoportancia table.
    
    Returns:
        dict: Rules with 'sistemas', 'autoportancia', etc.
    """
    global _BOM_RULES_CACHE
    if _BOM_RULES_CACHE is not None:
        return _BOM_RULES_CACHE
    
    # Try organized KB structure first, then fall back to root
    rules_path = Path(__file__).parent.parent / "01_KNOWLEDGE_BASE" / "Level_1_3_BOM_Rules" / "bom_rules.json"
    
    if not rules_path.exists():
        # Fallback to root directory
        rules_path = Path(__file__).parent / "bom_rules.json"
    
    if not rules_path.exists():
        raise FileNotFoundError(f"BOM rules not found at {rules_path}")
    
    with open(rules_path, 'r', encoding='utf-8') as f:
        _BOM_RULES_CACHE = json.load(f)
    
    return _BOM_RULES_CACHE


def _decimal_round(value: Decimal, places: int = 2) -> Decimal:
    """Round decimal to specified places using banker's rounding"""
    quantizer = Decimal(10) ** -places
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def _decimal_ceil(value: Decimal) -> int:
    """Ceiling function for Decimal values"""
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def validate_autoportancia(
    product_family: str,
    thickness_mm: int,
    span_m: float,
    safety_margin: float = 0.0
) -> AutoportanciaValidationResult:
    """
    Validate if requested span is within panel autoportancia limits.
    
    Autoportancia (self-supporting capacity) defines the maximum distance between
    supports (correas/vigas) that a panel can safely span. This function checks
    if the requested span exceeds structural limits against the exact manufacturer
    nominal limits (no safety margin by default).
    
    Args:
        product_family: Product family name (ISODEC_EPS, ISODEC_PIR, ISOROOF_3G, ISOPANEL_EPS)
        thickness_mm: Panel thickness in millimeters (50, 80, 100, 150, 200, 250)
        span_m: Requested distance between supports in meters
        safety_margin: Safety factor as decimal (default 0.0 = no margin, validates against nominal table)
    
    Returns:
        AutoportanciaValidationResult with validation status and recommendations
        
    Example:
        >>> result = validate_autoportancia("ISODEC_EPS", 100, 5.0)
        >>> print(result['is_valid'])  # True
        >>> print(result['span_max_safe_m'])  # 5.5 (exact nominal capacity for 100mm)
        
        >>> result = validate_autoportancia("ISODEC_EPS", 100, 8.0)
        >>> print(result['is_valid'])  # False
        >>> print(result['recommendation'])  # Suggests 150mm or 200mm thickness
    """
    # Load autoportancia table from BOM rules
    bom_rules = _load_bom_rules()
    autoportancia_tablas = bom_rules.get("autoportancia", {}).get("tablas", {})
    
    # Extract family base name (handle both "ISODEC_EPS" and "ISODEC_EPS_100mm" formats)
    family_base = product_family.split('_')
    if len(family_base) >= 2:
        # Join first two parts (e.g., ISODEC_EPS)
        family_key = f"{family_base[0]}_{family_base[1]}"
    else:
        family_key = product_family
    
    # Lookup span limit for this family and thickness
    family_data = autoportancia_tablas.get(family_key, {})
    thickness_data = family_data.get(str(thickness_mm), {})
    
    if not thickness_data:
        # Thickness not found - return neutral validation
        return AutoportanciaValidationResult(
            is_valid=True,
            span_requested_m=span_m,
            span_max_m=0.0,
            span_max_safe_m=0.0,
            excess_pct=0.0,
            recommendation=f"No autoportancia data available for {family_key} {thickness_mm}mm. Manual verification recommended.",
            alternative_thicknesses=[]
        )
    
    luz_max_m = thickness_data.get("luz_max_m", 0.0)
    peso_kg_m2 = thickness_data.get("peso_kg_m2", 0.0)
    
    # Calculate safe span with margin
    span_max_safe_m = luz_max_m * (1.0 - safety_margin)
    
    # Check validation
    is_valid = span_m <= span_max_safe_m
    excess_pct = ((span_m - span_max_safe_m) / span_max_safe_m * 100.0) if span_m > span_max_safe_m else 0.0
    
    # Generate recommendation if validation fails
    recommendation = ""
    alternative_thicknesses: List[int] = []
    
    if not is_valid:
        # Find alternative thicknesses that would work
        for thick_str, data in family_data.items():
            thick = int(thick_str)
            alt_luz_max = data.get("luz_max_m", 0.0)
            alt_safe = alt_luz_max * (1.0 - safety_margin)
            if span_m <= alt_safe and thick > thickness_mm:
                alternative_thicknesses.append(thick)
        
        alternative_thicknesses.sort()
        
        # Build recommendation message
        margin_text = f" (with {int(safety_margin*100)}% safety margin)" if safety_margin > 0 else ""
        recommendation = (
            f"⚠️  SPAN EXCEEDS NOMINAL AUTOPORTANCIA: Requested span of {span_m:.1f}m exceeds the nominal "
            f"autoportancia of {span_max_safe_m:.1f}m for {family_key} {thickness_mm}mm "
            f"(maximum {luz_max_m:.1f}m{margin_text}). "
        )
        
        if alternative_thicknesses:
            recommendation += f"Recommended: Use {alternative_thicknesses[0]}mm thickness instead. "
        else:
            intermediate_span = span_m / 2.0
            recommendation += (
                f"Recommended: Add intermediate support to reduce span to {intermediate_span:.1f}m. "
            )
        
        recommendation += f"(Excess: {excess_pct:.1f}%)"
    else:
        # Valid but provide informational message
        margin_used_pct = (span_m / luz_max_m) * 100.0
        margin_text = f" (with {int(safety_margin*100)}% safety margin)" if safety_margin > 0 else ""
        recommendation = (
            f"✓ Span validation PASSED: {span_m:.1f}m ≤ {span_max_safe_m:.1f}m within nominal capacity{margin_text} "
            f"(max {luz_max_m:.1f}m, using {margin_used_pct:.1f}% of absolute capacity)"
        )
    
    return AutoportanciaValidationResult(
        is_valid=is_valid,
        span_requested_m=span_m,
        span_max_m=luz_max_m,
        span_max_safe_m=span_max_safe_m,
        excess_pct=excess_pct,
        recommendation=recommendation,
        alternative_thicknesses=alternative_thicknesses
    )


def _product_to_specs(product_id: str, p: dict) -> ProductSpecs:
    """Convert product dict to ProductSpecs TypedDict.
    
    Helper function to avoid code duplication in lookup_product_specs.
    Includes defensive error handling for missing fields.
    
    Args:
        product_id: The product identifier
        p: Product dictionary from knowledge base
        
    Returns:
        ProductSpecs with all required fields
        
    Raises:
        KeyError: If required fields are missing from product dict
        ValueError: If product data is malformed
    """
    required_fields = [
        "name", "family", "sub_family", "thickness_mm", "price_per_m2",
        "currency", "ancho_util_m", "largo_min_m", "largo_max_m",
        "autoportancia_m", "stock_status"
    ]
    
    # Check for missing required fields
    missing = [field for field in required_fields if field not in p]
    if missing:
        raise KeyError(
            f"Product {product_id} is missing required fields: {', '.join(missing)}"
        )
    
    return ProductSpecs(
        product_id=product_id,
        name=p["name"],
        family=p["family"],
        sub_family=p["sub_family"],
        thickness_mm=p["thickness_mm"],
        price_per_m2=p["price_per_m2"],
        currency=p["currency"],
        ancho_util_m=p["ancho_util_m"],
        largo_min_m=p["largo_min_m"],
        largo_max_m=p["largo_max_m"],
        autoportancia_m=p["autoportancia_m"],
        stock_status=p["stock_status"]
    )


def lookup_product_specs(
    product_id: Optional[str] = None,
    family: Optional[str] = None,
    thickness_mm: Optional[int] = None,
    application: Optional[str] = None
) -> Optional[ProductSpecs]:
    """
    Look up product specifications from the knowledge base with indexed search.
    
    This is a DETERMINISTIC lookup - no LLM inference involved.
    
    Args:
        product_id: Exact product ID (e.g., "ISOPANEL_EPS_50mm")
        family: Product family (e.g., "ISOPANEL", "ISODEC", "ISOROOF")
        thickness_mm: Panel thickness in millimeters
        application: Application type (e.g., "techos", "paredes", "fachadas")
    
    Returns:
        ProductSpecs dictionary or None if not found
    """
    global _PRODUCT_INDEX_CACHE
    kb = _load_knowledge_base()
    products = kb.get("products", {})
    
    # Build index on first call with thread safety
    # Fast path: check if already initialized (no lock needed for read)
    if _PRODUCT_INDEX_CACHE is None:
        # Slow path: need to build index with lock
        with _product_index_lock:
            # Double-check inside lock (another thread may have built it)
            if _PRODUCT_INDEX_CACHE is None:
                _PRODUCT_INDEX_CACHE = _build_product_index(products)
    
    # Direct lookup by product_id - if specified, must match exactly
    if product_id:
        if product_id in products:
            return _product_to_specs(product_id, products[product_id])
        else:
            # product_id was specified but not found - return None
            return None
    
    # Search by criteria (only when no product_id specified)
    # Use index if both family and thickness are specified
    if family and thickness_mm is not None:
        family_upper = family.upper()
        candidate_ids = _PRODUCT_INDEX_CACHE["by_family_thickness"].get((family_upper, thickness_mm), [])
        
        # Filter by application if specified
        if application:
            app_lower = application.lower()
            for pid in candidate_ids:
                if app_lower in _PRODUCT_INDEX_CACHE["normalized_applications"].get(pid, []):
                    return _product_to_specs(pid, products[pid])
        elif candidate_ids:
            # No application filter, return first match
            return _product_to_specs(candidate_ids[0], products[candidate_ids[0]])
    
    # Fallback to linear search if index can't be used
    normalized_app = application.lower() if application else None
    for pid, p in products.items():
        match = True
        if family and p.get("family", "").upper() != family.upper():
            match = False
        if thickness_mm and p.get("thickness_mm") != thickness_mm:
            match = False
        if normalized_app:
            if normalized_app not in _PRODUCT_INDEX_CACHE["normalized_applications"].get(pid, []):
                match = False
        
        if match:
            return _product_to_specs(pid, p)
    
    return None


def calculate_panels_needed(ancho_total: float, ancho_util: float) -> int:
    """
    Calculate number of panels needed.
    Formula: ROUNDUP(Ancho Total / Ancho Útil)
    
    Uses Decimal for precision.
    """
    if ancho_total <= 0:
        raise ValueError("ancho_total must be greater than 0")
    if ancho_util <= 0:
        raise ValueError("ancho_util must be greater than 0")
    
    ancho_total_d = Decimal(str(ancho_total))
    ancho_util_d = Decimal(str(ancho_util))
    
    return _decimal_ceil(ancho_total_d / ancho_util_d)


def calculate_supports_needed(largo: float, autoportancia: float) -> int:
    """
    Calculate number of supports (apoyos) needed.
    Formula: ROUNDUP((Largo / Autoportancia) + 1)
    
    Uses Decimal for precision.
    """
    if autoportancia <= 0:
        raise ValueError("autoportancia must be greater than 0")
    
    largo_d = Decimal(str(largo))
    autoportancia_d = Decimal(str(autoportancia))
    
    return _decimal_ceil((largo_d / autoportancia_d) + 1)


def calculate_fixation_points(
    cantidad_paneles: int,
    apoyos: int,
    largo: float,
    installation_type: Literal["techo", "pared"] = "techo"
) -> int:
    """
    Calculate fixation points needed.
    
    For roof (techo):
        ROUNDUP(((Cantidad * Apoyos) * 2) + (Largo * 2 / 2.5))
    
    For wall (pared):
        ROUNDUP((Cantidad * Apoyos) * 2)
    """
    largo_d = Decimal(str(largo))
    
    if installation_type == "techo":
        base = Decimal(cantidad_paneles * apoyos * 2)
        edge_fixations = largo_d * 2 / Decimal("2.5")
        return _decimal_ceil(base + edge_fixations)
    else:
        return _decimal_ceil(Decimal(cantidad_paneles * apoyos * 2))


def calculate_accessories(
    cantidad_paneles: int,
    apoyos: int,
    largo: float,
    ancho_util: float,
    installation_type: Literal["techo", "pared"] = "techo"
) -> AccessoriesResult:
    """
    Calculate all accessories needed for the installation.
    
    All calculations use deterministic formulas from the knowledge base.
    """
    puntos_fijacion = calculate_fixation_points(
        cantidad_paneles, apoyos, largo, installation_type
    )
    
    largo_d = Decimal(str(largo))
    ancho_util_d = Decimal(str(ancho_util))
    
    # Rod quantity: ROUNDUP(puntos / 4)
    rod_quantity = _decimal_ceil(Decimal(puntos_fijacion) / Decimal("4"))
    
    # Front drip edge: ROUNDUP((cantidad * ancho_util) / 3)
    front_drip = _decimal_ceil(
        (Decimal(cantidad_paneles) * ancho_util_d) / Decimal("3")
    )
    
    # Lateral drip edge: ROUNDUP((largo * 2) / 3)
    lateral_drip = _decimal_ceil((largo_d * 2) / Decimal("3"))
    
    # Total profiles for rivets
    total_perfiles = front_drip + lateral_drip
    
    # Rivets: ROUNDUP(total_perfiles * 20)
    rivets = _decimal_ceil(Decimal(total_perfiles) * Decimal("20"))
    
    # Silicone: estimate based on perimeter
    perimetro = (Decimal(cantidad_paneles) * ancho_util_d * 2) + (largo_d * 2)
    silicone_tubes = _decimal_ceil(perimetro / Decimal("8"))
    
    return AccessoriesResult(
        panels_needed=cantidad_paneles,
        supports_needed=apoyos,
        fixation_points=puntos_fijacion,
        rod_quantity=rod_quantity,
        front_drip_edge_units=front_drip,
        lateral_drip_edge_units=lateral_drip,
        rivets_needed=rivets,
        silicone_tubes=silicone_tubes,
        metal_nuts=puntos_fijacion * 2,
        concrete_nuts=puntos_fijacion,
        concrete_anchors=puntos_fijacion,
        # V3: Initialize empty, will be filled by calculate_accessories_pricing
        line_items=[],
        accessories_subtotal_usd=0.0
    )


def calculate_accessories_pricing(
    accessories_quantities: AccessoriesResult,
    sistema: str = "techo_isodec_eps"
) -> tuple[List[QuotationLineItem], Decimal]:
    """
    V3 NEW: Calculate pricing for accessories based on quantities and system.
    
    Valorizes quantities using real prices from accessories_catalog.json.
    
    Args:
        accessories_quantities: Result from calculate_accessories()
        sistema: Construction system
    
    Returns:
        tuple of (line_items, subtotal_usd)
    """
    catalog = _load_accessories_catalog()
    accesorios = catalog.get('accesorios', [])
    indices = catalog.get('indices', {})
    by_tipo = indices.get('by_tipo', {})
    
    line_items = []
    
    def find_accessory(tipo: str) -> Optional[dict]:
        """Find first accessory by type"""
        items_indices = by_tipo.get(tipo, [])
        if items_indices and len(accesorios) > 0:
            # indices are array positions, not SKUs
            idx = items_indices[0]
            if idx < len(accesorios):
                return accesorios[idx]
        return None
    
    def _make_line(acc: dict, qty: int, rule_id: str, formula: str) -> QuotationLineItem:
        price = Decimal(str(acc['precio_unit_iva_inc']))
        subtotal = _decimal_round(Decimal(str(qty)) * price)
        return QuotationLineItem(
            product_id=acc['sku'], name=acc['name'], quantity=qty,
            area_m2=0.0, unit_price_usd=float(price), line_total_usd=float(subtotal),
            trace=LineItemTrace(
                rule_id=rule_id,
                formula=formula,
                source_file="accessories_catalog.json",
            ),
        )

    # Gotero frontal
    if accessories_quantities['front_drip_edge_units'] > 0:
        acc = find_accessory('gotero_frontal')
        if acc:
            line_items.append(_make_line(
                acc, accessories_quantities['front_drip_edge_units'],
                f"BOM-{sistema}-gotero_frontal", "gotero_frontal_piezas",
            ))

    # Gotero lateral
    if accessories_quantities['lateral_drip_edge_units'] > 0:
        acc = find_accessory('gotero_lateral')
        if acc:
            line_items.append(_make_line(
                acc, accessories_quantities['lateral_drip_edge_units'],
                f"BOM-{sistema}-gotero_lateral", "gotero_lateral_piezas",
            ))

    # Silicona
    if accessories_quantities['silicone_tubes'] > 0:
        acc = find_accessory('silicona')
        if acc:
            line_items.append(_make_line(
                acc, accessories_quantities['silicone_tubes'],
                f"BOM-{sistema}-silicona", "ceil(perimetro_ml / 8)",
            ))

    # Varillas
    if accessories_quantities['rod_quantity'] > 0:
        acc = find_accessory('varilla')
        if acc:
            line_items.append(_make_line(
                acc, accessories_quantities['rod_quantity'],
                f"BOM-{sistema}-varilla", "ceil(puntos_fijacion / 4)",
            ))
    
    # Calculate total
    total = sum(Decimal(str(item['line_total_usd'])) for item in line_items)
    return line_items, total


def calculate_panel_quote(
    product_id: str,
    length_m: float,
    width_m: float,
    quantity: int = 1,
    discount_percent: float = 0.0,
    include_accessories: bool = False,
    include_tax: bool = True,
    installation_type: Literal["techo", "pared"] = "techo",
    validate_span: bool = True
) -> QuotationResult:
    """
    Calculate DETERMINISTIC quotation for panel products.
    
    CRITICAL: The LLM NEVER executes this arithmetic - it only extracts parameters.
    All calculations use Python's Decimal for financial precision.
    
    Args:
        product_id: Product identifier (e.g., "ISOPANEL_EPS_50mm")
        length_m: Panel length in meters (largo)
        width_m: Total width to cover in meters (ancho total)
        quantity: Number of identical panels/installations
        discount_percent: Discount percentage (0-30)
        include_accessories: Whether to calculate accessories
        include_tax: Whether to include IVA (22%)
        installation_type: "techo" or "pared"
        validate_span: Whether to validate autoportancia limits (default True)
    
    Returns:
        QuotationResult with all calculations verified
        
    Raises:
        ValueError: If product not found or parameters invalid
    """
    # Load KB and validate product
    kb = _load_knowledge_base()
    products = kb.get("products", {})
    
    if product_id not in products:
        raise ValueError(f"Product not found: {product_id}")
    
    product = products[product_id]
    pricing_rules = kb.get("pricing_rules", {})
    
    # Validate parameters
    if length_m <= 0 or width_m <= 0:
        raise ValueError("Dimensions must be greater than 0")
    
    # Validate dimensions and adjust for cut-to-length
    largo_min = product["largo_min_m"]
    largo_max = product["largo_max_m"]
    adjusted_length = length_m
    cutting_notes = []
    
    # If length is below minimum, calculate cut-to-length solution
    if length_m < largo_min:
        # Calculate how many minimum panels can be cut from one panel
        cutting_waste_per_cut = 0.01  # 1cm waste per cut
        usable_length_per_panel = largo_min - cutting_waste_per_cut
        panels_per_stock = int(usable_length_per_panel / length_m)
        
        if panels_per_stock > 0:
            adjusted_length = largo_min
            cutting_notes.append(
                f"Largo solicitado {length_m}m es menor al mínimo de producción ({largo_min}m). "
                f"Se entregarán paneles de {largo_min}m para cortar en obra. "
                f"De cada panel se pueden obtener {panels_per_stock} piezas de {length_m}m "
                f"(considerando 1cm de desperdicio por corte)."
            )
        else:
            raise ValueError(
                f"Largo {length_m}m demasiado corto. "
                f"Mínimo recomendado: {largo_min / 2}m para corte en obra."
            )
    
    if length_m > largo_max:
        raise ValueError(f"Length {length_m}m exceeds maximum {largo_max}m")
    
    if discount_percent < 0 or discount_percent > product["calculation_rules"]["max_discount_percent"]:
        raise ValueError(f"Discount must be between 0 and {product['calculation_rules']['max_discount_percent']}%")
    
    if quantity < 1:
        raise ValueError("Quantity must be at least 1")
    
    # Validate autoportancia (span limits) if requested
    autoportancia_validation = None
    if validate_span:
        autoportancia_validation = validate_autoportancia(
            product_family=product["family"],
            thickness_mm=product["thickness_mm"],
            span_m=length_m,
            safety_margin=0.0
        )
    
    # === DETERMINISTIC CALCULATIONS WITH DECIMAL ===
    
    # Convert to Decimal for precision (use adjusted length for pricing)
    length_d = Decimal(str(adjusted_length))
    width_d = Decimal(str(width_m))
    price_per_m2_d = Decimal(str(product["price_per_m2"]))
    discount_d = Decimal(str(discount_percent))
    tax_rate_d = Decimal(str(pricing_rules.get("tax_rate_uy_iva", 0.22)))
    ancho_util_d = Decimal(str(product["ancho_util_m"]))
    
    # Calculate area per panel
    area_per_panel = _decimal_round(length_d * width_d)
    
    # Calculate panels needed (if width > ancho_util)
    panels_needed = calculate_panels_needed(float(width_d), product["ancho_util_m"])
    
    # Effective coverage area
    effective_area = _decimal_round(length_d * (ancho_util_d * panels_needed))
    
    # Unit price based on area
    unit_price = _decimal_round(area_per_panel * price_per_m2_d)
    
    # Subtotal for all quantities
    subtotal = _decimal_round(effective_area * price_per_m2_d * Decimal(quantity))
    
    # Apply bulk discount if applicable
    bulk_rules = product["calculation_rules"]
    total_m2 = float(effective_area) * quantity
    
    actual_discount = discount_d
    if total_m2 >= bulk_rules["bulk_discount_threshold_m2"]:
        bulk_discount = Decimal(str(bulk_rules["bulk_discount_percent"]))
        actual_discount = max(discount_d, bulk_discount)
    
    # Calculate discount amount
    discount_amount = _decimal_round(subtotal * actual_discount / Decimal("100"))
    
    # Total before tax
    total_before_tax = _decimal_round(subtotal - discount_amount)
    
    # Tax
    tax_amount = Decimal("0")
    if include_tax:
        tax_amount = _decimal_round(total_before_tax * tax_rate_d)
    
    # Total
    total = _decimal_round(total_before_tax + tax_amount)
    
    # Accessories calculation
    accessories = None
    accessories_total = Decimal("0")
    
    if include_accessories:
        apoyos = calculate_supports_needed(length_m, product["autoportancia_m"])
        accessories = calculate_accessories(
            panels_needed * quantity,
            apoyos,
            length_m,
            product["ancho_util_m"],
            installation_type
        )
        
        # V3 NEW: Valorize accessories using catalog prices
        # Auto-detect sistema based on product family if needed
        family = product.get("family", "").upper()
        if "ISODEC" in family:
            sistema = "techo_isodec_eps" if "EPS" in product.get("sub_family", "").upper() else "techo_isodec_pir"
        elif "ISOROOF" in family:
            sistema = "techo_isoroof_3g"
        elif "ISOPANEL" in family:
            sistema = "pared_isopanel_eps"
        elif "ISOWALL" in family:
            sistema = "pared_isowall_pir"
        elif "ISOFRIG" in family:
            sistema = "pared_isofrig_pir"
        else:
            sistema = "techo_isodec_eps"  # default
        
        # Calculate accessories pricing
        accessories_line_items, accessories_total = calculate_accessories_pricing(
            accessories,
            sistema
        )
        
        # Update accessories result with pricing
        accessories['line_items'] = accessories_line_items
        accessories['accessories_subtotal_usd'] = float(accessories_total)
    
    # Grand total
    grand_total = _decimal_round(total + accessories_total)
    
    # Check for waste optimization opportunities
    optimization_suggestion = suggest_optimization(
        product_id=product_id,
        length_m=length_m,
        width_m=width_m,
        quantity=quantity,
        waste_threshold_pct=5.0
    )
    
    # Add optimization suggestion to notes if applicable
    if optimization_suggestion:
        cutting_notes.append(optimization_suggestion["message"])
    
    # Generate quotation ID
    import uuid
    from datetime import datetime
    quotation_id = f"QT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    return QuotationResult(
        quotation_id=quotation_id,
        product_id=product_id,
        product_name=product["name"],
        
        length_m=float(length_m),  # Requested length
        actual_length_m=float(adjusted_length),  # Actual panel length delivered
        width_m=float(width_d),
        area_m2=float(effective_area),
        
        panels_needed=panels_needed,
        unit_price_per_m2=float(price_per_m2_d),
        
        subtotal_usd=float(subtotal),
        discount_percent=float(actual_discount),
        discount_amount_usd=float(discount_amount),
        total_before_tax_usd=float(total_before_tax),
        tax_amount_usd=float(tax_amount),
        total_usd=float(total),
        
        accessories=accessories,
        accessories_total_usd=float(accessories_total),
        
        grand_total_usd=float(grand_total),
        
        # Autoportancia validation result (if enabled)
        autoportancia_validation=autoportancia_validation,
        
        # CRITICAL: This flag indicates calculation was done by Python, not LLM
        calculation_verified=True,
        calculation_method="python_decimal_deterministic",
        currency="USD",
        notes=cutting_notes,
        trace_log=[
            {"rule_id": "PANEL-AREA", "formula": f"ceil({width_m} / {ancho_util_m})", "result": panels_needed},
            {"rule_id": "PANEL-PRICE", "formula": f"{area_m2} * {unit_price_per_m2}", "result": float(subtotal)},
        ] + ([
            {"rule_id": f"AUTOP-{product_id}", "formula": f"span={length_m}m <= max={autoportancia_validation.get('span_max_m', 'N/A')}m", "result": autoportancia_validation.get("is_valid")}
        ] if autoportancia_validation else [])
    )


def suggest_optimization(
    product_id: str,
    length_m: float,
    width_m: float,
    quantity: int = 1,
    waste_threshold_pct: float = 5.0,
) -> Optional[dict]:
    """
    Detect if material waste (offcut) exceeds the given threshold and suggest
    an optimized panel length that reduces waste.

    The function compares the requested length against the panel's standard
    production lengths (or minimum increments) to find a shorter length that
    would keep waste below the threshold.

    Args:
        product_id: Product ID (e.g., "ISOPANEL_EPS_50mm")
        length_m: Requested panel length in meters
        width_m: Total width to cover in meters
        quantity: Number of panels/installations
        waste_threshold_pct: Maximum acceptable waste percentage (default 5%)

    Returns:
        dict with optimization suggestion if waste exceeds threshold, None otherwise.
        The dict contains:
        - "waste_pct": current waste percentage
        - "suggested_length_m": optimized length
        - "savings_m2": area saved
        - "savings_usd": estimated USD saved
        - "message": human-readable suggestion in Spanish
    """
    # Look up the product specs
    product = lookup_product_specs(product_id=product_id)
    if not product:
        return None
    
    # Calculate panels needed based on width coverage
    panels_needed = calculate_panels_needed(width_m, product["ancho_util_m"])
    
    # Calculate total ordered area (what we're actually buying)
    total_area = length_m * panels_needed * quantity * product["ancho_util_m"]
    
    # Calculate effective/useful area (what we actually need to cover)
    useful_area = length_m * width_m * quantity
    
    # Guard against division by zero
    if total_area <= 0:
        return None
    
    # Compute waste percentage
    waste_pct = ((total_area - useful_area) / total_area) * 100.0
    
    # If waste is within acceptable threshold, no optimization needed
    if waste_pct <= waste_threshold_pct:
        return None
    
    # Try to find optimized length using binary search (much faster than linear)
    # We need to ensure we still cover the width
    step_m = OPTIMIZATION_STEP_M
    
    # Binary search for the optimal length
    min_length = product["largo_min_m"]
    max_length = length_m
    suggested_length_m = length_m
    best_length = length_m
    
    # Use binary search if the range is large enough to benefit (at least 10 steps)
    if (max_length - min_length) > BINARY_SEARCH_MIN_RANGE_M:
        # Binary search to find the point where waste crosses threshold
        prev_mid_length = None  # Track previous mid_length to detect convergence
        
        while (max_length - min_length) >= step_m:
            mid_length = (min_length + max_length) / 2.0
            # Round to nearest 5cm step
            mid_length = round(mid_length / step_m) * step_m
            
            # Ensure mid_length doesn't equal boundaries (would cause infinite loop)
            if mid_length <= min_length:
                mid_length = min_length + step_m
            elif mid_length >= max_length:
                mid_length = max_length - step_m
            
            # Break if we can't make progress or if mid_length hasn't changed
            if mid_length <= min_length or mid_length >= max_length:
                break
            if prev_mid_length is not None and abs(mid_length - prev_mid_length) < step_m / 2:
                # Converged - mid_length isn't changing meaningfully
                break
            
            prev_mid_length = mid_length
            
            # Calculate waste at this length
            test_total_area = mid_length * panels_needed * quantity * product["ancho_util_m"]
            test_useful_area = mid_length * width_m * quantity
            
            if test_total_area <= 0:
                min_length = mid_length + step_m
                continue
            
            test_waste_pct = ((test_total_area - test_useful_area) / test_total_area) * 100.0
            
            if test_waste_pct <= waste_threshold_pct:
                # Waste is acceptable, try shorter length
                best_length = mid_length
                max_length = mid_length - step_m  # Move boundary away from mid
            else:
                # Waste too high, need longer panel
                min_length = mid_length + step_m  # Move boundary away from mid
        
        suggested_length_m = best_length
    else:
        # Range is small, use linear search
        max_iterations = int((length_m - min_length) / step_m)
        for i in range(1, max_iterations):
            test_length = length_m - (i * step_m)
            if test_length < min_length:
                break
            
            # Recalculate with test length
            test_total_area = test_length * panels_needed * quantity * product["ancho_util_m"]
            test_useful_area = test_length * width_m * quantity
            
            # Guard against division by zero
            if test_total_area <= 0:
                continue
            
            test_waste_pct = ((test_total_area - test_useful_area) / test_total_area) * 100.0
            
            # Check if this brings waste below threshold
            if test_waste_pct <= waste_threshold_pct:
                suggested_length_m = test_length
                break
    
    # If we couldn't find a better length, return None
    if suggested_length_m == length_m:
        return None
    
    # Calculate savings
    savings_m2 = (length_m - suggested_length_m) * panels_needed * quantity * product["ancho_util_m"]
    savings_usd = savings_m2 * product["price_per_m2"]
    delta_cm = (length_m - suggested_length_m) * 100
    
    # Generate Spanish message
    message = (
        f"SUGERENCIA: Reducir largo en {delta_cm:.0f} cm "
        f"(de {length_m:.2f}m a {suggested_length_m:.2f}m) "
        f"ahorra {savings_usd:.2f} USD ({savings_m2:.2f} m² menos de desperdicio)."
    )
    
    return {
        "waste_pct": waste_pct,
        "suggested_length_m": suggested_length_m,
        "savings_m2": savings_m2,
        "savings_usd": savings_usd,
        "message": message
    }


def validate_quotation(result: QuotationResult) -> tuple[bool, List[str]]:
    """
    Validate a quotation result for consistency.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # CRITICAL: Verify calculation was done by code, not LLM
    if not result.get("calculation_verified"):
        errors.append("CRITICAL: calculation_verified is False - LLM may have calculated")
    
    if result.get("calculation_method") != "python_decimal_deterministic":
        errors.append(f"Unexpected calculation method: {result.get('calculation_method')}")
    
    # Validate numeric consistency
    if result["total_usd"] <= 0:
        errors.append("Total USD must be greater than 0")
    
    if result["area_m2"] <= 0:
        errors.append("Area must be greater than 0")
    
    if result["panels_needed"] < 1:
        errors.append("Must need at least 1 panel")
    
    # Validate discount application
    expected_discount = Decimal(str(result["subtotal_usd"])) * Decimal(str(result["discount_percent"])) / Decimal("100")
    expected_discount = float(_decimal_round(expected_discount))
    
    if abs(result["discount_amount_usd"] - expected_discount) > 0.01:
        errors.append(f"Discount calculation mismatch: {result['discount_amount_usd']} vs expected {expected_discount}")
    
    # Validate total calculation
    expected_total_before_tax = result["subtotal_usd"] - result["discount_amount_usd"]
    if abs(result["total_before_tax_usd"] - expected_total_before_tax) > 0.01:
        errors.append("Total before tax calculation mismatch")
    
    return (len(errors) == 0, errors)


# Tool definitions for LLM integration
TOOL_DEFINITIONS = [
    {
        "name": "calculate_panel_quote",
        "description": "Calcula cotización exacta para paneles térmicos BMC. USAR SIEMPRE para cualquier cálculo de precio. El LLM NUNCA debe calcular precios directamente.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID del producto (ej: ISOPANEL_EPS_50mm, ISODEC_EPS_100mm, ISOROOF_3G)"
                },
                "length_m": {
                    "type": "number",
                    "minimum": 0.5,
                    "maximum": 14.0,
                    "description": "Largo del panel en metros"
                },
                "width_m": {
                    "type": "number",
                    "minimum": 0.5,
                    "maximum": 50.0,
                    "description": "Ancho total a cubrir en metros"
                },
                "quantity": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                    "description": "Cantidad de instalaciones/paneles"
                },
                "discount_percent": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 30,
                    "default": 0,
                    "description": "Porcentaje de descuento aplicable"
                },
                "include_accessories": {
                    "type": "boolean",
                    "default": False,
                    "description": "Incluir cálculo de accesorios"
                },
                "include_tax": {
                    "type": "boolean",
                    "default": True,
                    "description": "Incluir IVA (22%)"
                },
                "installation_type": {
                    "type": "string",
                    "enum": ["techo", "pared"],
                    "default": "techo",
                    "description": "Tipo de instalación"
                }
            },
            "required": ["product_id", "length_m", "width_m"]
        }
    },
    {
        "name": "lookup_product_specs",
        "description": "Busca especificaciones de un producto en la base de conocimiento. Usar para consultar precios, dimensiones y disponibilidad.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID exacto del producto"
                },
                "family": {
                    "type": "string",
                    "enum": ["ISOPANEL", "ISODEC", "ISOWALL", "ISOROOF", "HIANSA"],
                    "description": "Familia de producto"
                },
                "thickness_mm": {
                    "type": "integer",
                    "description": "Espesor en milímetros"
                },
                "application": {
                    "type": "string",
                    "enum": ["techos", "paredes", "fachadas", "cubiertas", "agro"],
                    "description": "Tipo de aplicación"
                }
            }
        }
    },
    {
        "name": "calculate_accessories",
        "description": "Calcula accesorios necesarios para la instalación de paneles.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "cantidad_paneles": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Cantidad de paneles"
                },
                "apoyos": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Cantidad de apoyos"
                },
                "largo": {
                    "type": "number",
                    "description": "Largo en metros"
                },
                "ancho_util": {
                    "type": "number",
                    "description": "Ancho útil del panel en metros"
                },
                "installation_type": {
                    "type": "string",
                    "enum": ["techo", "pared"],
                    "default": "techo"
                }
            },
            "required": ["cantidad_paneles", "apoyos", "largo", "ancho_util"]
        }
    }
]
