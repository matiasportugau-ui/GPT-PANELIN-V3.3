# OpenAI Ecosystem Helpers

Utilities in `client.py` normalize outputs from different OpenAI API response shapes.

## `extract_text(response)` behavior

`extract_text` now supports:

- Responses API style (`response.output_text`)
- Responses API itemized content (`response.output[].content[]`)
- Chat Completions (`response.choices[].message.content` as string or parts)
- Message-oriented variants (`response.message.content`, `response.messages[]`)

### Examples

#### 1) Plain text response

```python
payload = {
    "output": [
        {"type": "message", "content": [{"type": "output_text", "text": "Hello from model"}]}
    ]
}

extract_text(payload)
# "Hello from model"
```

#### 2) Chat completion content parts

```python
payload = {
    "choices": [
        {
            "message": {
                "content": [
                    {"type": "text", "text": "First line."},
                    {"type": "text", "text": "Second line."},
                ]
            }
        }
    ]
}

extract_text(payload)
# "First line.\nSecond line."
```

#### 3) No text available

```python
payload = {
    "output": [
        {"type": "tool_call", "name": "lookup_price", "arguments": {"sku": "ABC-123"}}
    ]
}

extract_text(payload)
# "[no text content; item_types=tool_call; content_types=none]"
```

This diagnostic string is compact and is intended for CLI logs when the model returned only structured/tool data.

## Optional helper: `extract_primary_output(response)`

When you need richer handling than plain text, use `extract_primary_output`.

Returned shape:

- `{"type": "text", "value": "..."}`
- `{"type": "structured", "value": {...}}`
- `{"type": "tool_call", "value": {"name": "...", "arguments": {...}, "id": "..."}}`
- `{"type": "unknown", "value": null, "diagnostic": "..."}`

### Structured example

```python
payload = {
    "parsed": {"answer": "42", "confidence": 0.91}
}

extract_primary_output(payload)
# {"type": "structured", "value": {"answer": "42", "confidence": 0.91}}
```

### Tool-call example

```python
payload = {
    "message": {
        "tool_calls": [
            {
                "id": "call_1",
                "function": {"name": "search_catalog", "arguments": {"query": "isodec 100"}},
            }
        ]
    }
}

extract_primary_output(payload)
# {"type": "tool_call", "value": {"name": "search_catalog", "arguments": {"query": "isodec 100"}, "id": "call_1"}}
```

## Expected CLI behavior

For command-line apps that print model results:

1. Call `extract_primary_output(response)`.
2. If `type == "text"`, print `value` as-is.
3. If `type == "structured"`, pretty-print JSON payload.
4. If `type == "tool_call"`, print a short tool invocation line (name + arguments summary).
5. Otherwise, print the `diagnostic` to aid debugging without flooding logs.

This keeps output user-friendly while still exposing non-text responses clearly.
