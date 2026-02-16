# KB Pipeline

`kb_pipeline` builds lightweight MCP lookup artifacts and provenance metadata from the three source catalogs:

- `shopify_catalog_v1.json`
- `bromyros_pricing_master.json`
- `bromyros_pricing_gpt_optimized.json`

## Rebuild command

```bash
python kb_pipeline/build_indexes.py
```

## Outputs

- `artifacts/hot/shopify_catalog_v1.hot.json`
- `artifacts/hot/bromyros_pricing_master.hot.json`
- `artifacts/hot/bromyros_pricing_gpt_optimized.hot.json`
- `artifacts/source_manifest.json`

Each hot record preserves immutable source references:

- `source_file`
- `source_key`
- `checksum`

## Validation rules

The build fails if:

1. Any required field is missing or empty (`sku`, `title`, `category`, `price`, `availability`, `source_file`, `source_key`, `checksum`).
2. Duplicate `sku` values exist within the same source catalog.
3. Duplicate immutable source references (`source_key` + `checksum`) are detected across catalogs.

## Expected artifact sizes and row counts

Current expected outputs after running the rebuild command:

| Artifact | Rows | Approx. size |
|---|---:|---:|
| `artifacts/hot/shopify_catalog_v1.hot.json` | 1 | 470 bytes |
| `artifacts/hot/bromyros_pricing_master.hot.json` | 96 | 31,969 bytes |
| `artifacts/hot/bromyros_pricing_gpt_optimized.hot.json` | 96 | 32,161 bytes |
| `artifacts/source_manifest.json` | n/a | 1,488 bytes |
