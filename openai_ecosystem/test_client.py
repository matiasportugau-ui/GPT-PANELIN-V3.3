"""
Tests for openai_ecosystem.client module.

Comprehensive test coverage for extract_text function covering:
- Various response shapes (Responses API, Chat Completions, message variants)
- Edge cases (empty responses, None values, malformed structures)
- Deduplication behavior
- Diagnostic message generation
"""

import pytest
import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai_ecosystem.client import extract_text, extract_primary_output


class TestExtractTextResponseShapes:
    """Test extract_text with various OpenAI API response shapes."""

    def test_direct_output_text(self):
        """Test direct output_text field extraction."""
        response = {"output_text": "Hello, world!"}
        assert extract_text(response) == "Hello, world!"

    def test_chat_completions_string_content(self):
        """Test Chat Completions API with string message content."""
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is a response."
                    }
                }
            ]
        }
        assert extract_text(response) == "This is a response."

    def test_chat_completions_multiple_choices(self):
        """Test Chat Completions API with multiple choices."""
        response = {
            "choices": [
                {"message": {"content": "First choice"}},
                {"message": {"content": "Second choice"}}
            ]
        }
        result = extract_text(response)
        assert "First choice" in result
        assert "Second choice" in result

    def test_responses_api_with_output_array(self):
        """Test Responses API with output array containing content parts."""
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "text", "text": "Part one"},
                        {"type": "text", "text": "Part two"}
                    ]
                }
            ]
        }
        result = extract_text(response)
        assert "Part one" in result
        assert "Part two" in result

    def test_message_centric_variant(self):
        """Test message-centric response variant."""
        response = {
            "message": {
                "content": "Message content"
            }
        }
        assert extract_text(response) == "Message content"

    def test_messages_array(self):
        """Test messages array variant."""
        response = {
            "messages": [
                {"content": "First message"},
                {"content": "Second message"}
            ]
        }
        result = extract_text(response)
        assert "First message" in result
        assert "Second message" in result

    def test_structured_content_with_nested_parts(self):
        """Test structured content arrays with nested text parts."""
        response = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "Output text"},
                        {"type": "message_text", "value": "Message value"},
                        {"type": "input_text", "text": "Input text"}
                    ]
                }
            ]
        }
        result = extract_text(response)
        assert "Output text" in result
        assert "Message value" in result
        assert "Input text" in result

    def test_chat_completions_with_content_parts(self):
        """Test Chat Completions with structured content parts."""
        response = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "Text part 1"},
                            {"type": "text", "text": "Text part 2"}
                        ]
                    }
                }
            ]
        }
        result = extract_text(response)
        assert "Text part 1" in result
        assert "Text part 2" in result


class TestExtractTextEdgeCases:
    """Test extract_text with edge cases and malformed structures."""

    def test_empty_dict(self):
        """Test with empty dictionary."""
        response = {}
        result = extract_text(response)
        assert result.startswith("[no text content;")
        assert "top-level keys=[]" in result

    def test_none_response(self):
        """Test with None response."""
        response = None
        result = extract_text(response)
        assert result.startswith("[no text content;")

    def test_empty_string_content(self):
        """Test with empty string content."""
        response = {"output_text": ""}
        result = extract_text(response)
        assert result.startswith("[no text content;")

    def test_whitespace_only_content(self):
        """Test with whitespace-only content."""
        response = {"output_text": "   \n\t  "}
        result = extract_text(response)
        assert result.startswith("[no text content;")

    def test_none_values_in_structure(self):
        """Test with None values in various fields."""
        response = {
            "output_text": None,
            "choices": [{"message": {"content": None}}],
            "message": None
        }
        result = extract_text(response)
        assert result.startswith("[no text content;")

    def test_empty_arrays(self):
        """Test with empty arrays."""
        response = {
            "choices": [],
            "output": [],
            "messages": []
        }
        result = extract_text(response)
        assert result.startswith("[no text content;")

    def test_malformed_choices_structure(self):
        """Test with malformed choices structure."""
        response = {
            "choices": [
                {"message": {}},
                {"no_message_key": "value"}
            ]
        }
        result = extract_text(response)
        assert result.startswith("[no text content;")

    def test_non_string_content_values(self):
        """Test with non-string content values."""
        response = {
            "choices": [
                {"message": {"content": 123}},
                {"message": {"content": True}},
                {"message": {"content": ["not", "a", "string"]}}
            ]
        }
        result = extract_text(response)
        # Should handle gracefully and produce diagnostic
        assert isinstance(result, str)

    def test_mixed_valid_and_invalid_content(self):
        """Test with mix of valid and invalid content."""
        response = {
            "choices": [
                {"message": {"content": "Valid text"}},
                {"message": {"content": None}},
                {"message": {"content": ""}}
            ]
        }
        result = extract_text(response)
        assert result == "Valid text"

    def test_deeply_nested_empty_structures(self):
        """Test with deeply nested but empty structures."""
        response = {
            "output": [
                {
                    "content": [
                        {"type": "text", "text": ""},
                        {"type": "text", "value": ""}
                    ]
                }
            ]
        }
        result = extract_text(response)
        assert result.startswith("[no text content;")


class TestExtractTextDeduplication:
    """Test deduplication behavior in extract_text."""

    def test_duplicate_text_removal(self):
        """Test that duplicate text snippets are removed."""
        response = {
            "choices": [
                {"message": {"content": "Same text"}},
                {"message": {"content": "Same text"}},
                {"message": {"content": "Different text"}}
            ]
        }
        result = extract_text(response)
        # Should only contain each unique text once
        assert result.count("Same text") == 1
        assert "Different text" in result

    def test_whitespace_normalized_deduplication(self):
        """Test that whitespace is normalized before deduplication."""
        response = {
            "messages": [
                {"content": "  Text with spaces  "},
                {"content": "Text with spaces"}
            ]
        }
        result = extract_text(response)
        # After trimming, both should be deduplicated
        assert result == "Text with spaces"

    def test_preserves_order_of_unique_items(self):
        """Test that order of unique items is preserved."""
        response = {
            "choices": [
                {"message": {"content": "First"}},
                {"message": {"content": "Second"}},
                {"message": {"content": "First"}},
                {"message": {"content": "Third"}}
            ]
        }
        result = extract_text(response)
        lines = result.split("\n")
        assert lines[0] == "First"
        assert lines[1] == "Second"
        assert lines[2] == "Third"
        assert len(lines) == 3

    def test_empty_strings_not_included(self):
        """Test that empty strings after stripping are not included."""
        response = {
            "messages": [
                {"content": "Valid text"},
                {"content": ""},
                {"content": "   "},
                {"content": "Another valid text"}
            ]
        }
        result = extract_text(response)
        assert "Valid text" in result
        assert "Another valid text" in result
        # Should not have empty lines from empty/whitespace content
        lines = [line for line in result.split("\n") if line]
        assert len(lines) == 2

    def test_duplicate_across_different_shapes(self):
        """Test deduplication across different response shape locations."""
        response = {
            "output_text": "Duplicate content",
            "choices": [
                {"message": {"content": "Duplicate content"}},
                {"message": {"content": "Unique content"}}
            ]
        }
        result = extract_text(response)
        # output_text is checked first and should short-circuit
        assert result == "Duplicate content"


class TestExtractTextDiagnostics:
    """Test diagnostic message generation when no text is available."""

    def test_diagnostic_with_item_types(self):
        """Test diagnostic includes item types when present."""
        response = {
            "output": [
                {"type": "image", "data": "..."},
                {"type": "tool_call", "name": "function"}
            ]
        }
        result = extract_text(response)
        assert result.startswith("[no text content;")
        assert "item_types=" in result
        assert "image" in result
        assert "tool_call" in result

    def test_diagnostic_with_content_types(self):
        """Test diagnostic includes content types from nested structures."""
        response = {
            "output": [
                {
                    "content": [
                        {"type": "image"},
                        {"type": "audio"}
                    ]
                }
            ]
        }
        result = extract_text(response)
        assert result.startswith("[no text content;")
        assert "content_types=" in result
        assert "audio" in result or "image" in result

    def test_diagnostic_with_top_level_keys(self):
        """Test diagnostic shows top-level keys when no types available."""
        response = {
            "id": "123",
            "model": "gpt-4",
            "created": 1234567890,
            "usage": {"total_tokens": 100}
        }
        result = extract_text(response)
        assert result.startswith("[no text content;")
        assert "top-level keys=" in result
        assert "id" in result or "model" in result

    def test_diagnostic_limits_key_count(self):
        """Test that diagnostic limits the number of keys shown."""
        response = {f"key{i}": f"value{i}" for i in range(20)}
        result = extract_text(response)
        assert result.startswith("[no text content;")
        # Should limit to 8 keys (extract the keys list from result)
        keys_match = re.search(r"top-level keys=\[(.*?)\]", result)
        if keys_match:
            keys_str = keys_match.group(1)
            # Count comma-separated items
            keys_list = [k.strip().strip("'") for k in keys_str.split(",") if k.strip()]
            assert len(keys_list) <= 8

    def test_diagnostic_with_object_like_response(self):
        """Test diagnostic with object-like (non-dict) response."""
        class MockResponse:
            def __init__(self):
                self.id = "123"
                self.model = "gpt-4"
                self.choices = []
        
        response = MockResponse()
        result = extract_text(response)
        assert result.startswith("[no text content;")
        assert "top-level keys=" in result

    def test_diagnostic_deduplicates_types(self):
        """Test that diagnostic deduplicates repeated types."""
        response = {
            "output": [
                {"type": "image"},
                {"type": "image"},
                {"type": "audio"},
                {"type": "image"}
            ]
        }
        result = extract_text(response)
        assert result.startswith("[no text content;")
        # Should show sorted unique types
        assert "audio" in result
        assert "image" in result
        # Check that it's sorted (audio before image)
        audio_pos = result.find("audio")
        image_pos = result.find("image")
        assert audio_pos < image_pos


class TestExtractPrimaryOutput:
    """Test extract_primary_output function."""

    def test_returns_text_type_when_text_available(self):
        """Test that text type is returned when text is available."""
        response = {"output_text": "Hello"}
        result = extract_primary_output(response)
        assert result["type"] == "text"
        assert result["value"] == "Hello"

    def test_returns_structured_type_for_parsed_output(self):
        """Test that structured type is returned for parsed output."""
        response = {"parsed": {"key": "value"}}
        result = extract_primary_output(response)
        assert result["type"] == "structured"
        assert result["value"] == {"key": "value"}

    def test_returns_tool_call_type_for_tool_calls(self):
        """Test that tool_call type is returned for tool calls."""
        response = {
            "output": [
                {
                    "type": "tool_call",
                    "name": "get_weather",
                    "arguments": {"city": "Boston"}
                }
            ]
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        assert result["value"]["name"] == "get_weather"
        assert result["value"]["arguments"] == {"city": "Boston"}


    def test_parses_tool_call_arguments_json_string(self):
        """Tool-call arguments serialized as JSON string are parsed."""
        response = {
            "message": {
                "tool_calls": [
                    {
                        "id": "call_2",
                        "function": {
                            "name": "price_check",
                            "arguments": '{"query": "ISODEC-100-1000", "filter_type": "sku"}'
                        }
                    }
                ]
            }
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        assert result["value"]["arguments"] == {
            "query": "ISODEC-100-1000",
            "filter_type": "sku"
        }
        assert result["value"]["expected_contract_version"] == "v1"

    def test_parses_tool_call_arguments_empty_or_whitespace_string(self):
        """Empty or whitespace-only arguments strings are treated as empty dict."""
        response = {
            "message": {
                "tool_calls": [
                    {
                        "id": "call_empty",
                        "function": {
                            "name": "price_check",
                            "arguments": ""
                        },
                    }
                ]
            }
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        assert result["value"]["arguments"] == {}

        response_whitespace = {
            "message": {
                "tool_calls": [
                    {
                        "id": "call_ws",
                        "function": {
                            "name": "price_check",
                            "arguments": "   \n\t  "
                        },
                    }
                ]
            }
        }
        result_ws = extract_primary_output(response_whitespace)
        assert result_ws["type"] == "tool_call"
        assert result_ws["value"]["arguments"] == {}

    def test_parses_tool_call_arguments_none(self):
        """None arguments are treated as empty dict."""
        response = {
            "message": {
                "tool_calls": [
                    {
                        "id": "call_none",
                        "function": {
                            "name": "price_check",
                            "arguments": None
                        },
                    }
                ]
            }
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        assert result["value"]["arguments"] == {}

    def test_parses_tool_call_arguments_pass_through_dict_and_list(self):
        """Dict and list arguments are passed through without JSON parsing."""
        dict_args = {"query": "ISODEC-100-1000", "filter_type": "sku"}
        response_dict = {
            "message": {
                "tool_calls": [
                    {
                        "id": "call_dict",
                        "function": {
                            "name": "price_check",
                            "arguments": dict_args,
                        },
                    }
                ]
            }
        }
        result_dict = extract_primary_output(response_dict)
        assert result_dict["type"] == "tool_call"
        assert result_dict["value"]["arguments"] == dict_args

        list_args = ["ISODEC-100-1000", "ISODEC-200-1000"]
        response_list = {
            "message": {
                "tool_calls": [
                    {
                        "id": "call_list",
                        "function": {
                            "name": "price_check",
                            "arguments": list_args,
                        },
                    }
                ]
            }
        }
        result_list = extract_primary_output(response_list)
        assert result_list["type"] == "tool_call"
        assert result_list["value"]["arguments"] == list_args

    def test_extracts_tool_call_from_content_parts(self):
        """Tool-call metadata nested under content[] is detected."""
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "function_call",
                            "name": "catalog_search",
                            "arguments": {"query": "isodec"}
                        }
                    ]
                }
            ]
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        assert result["value"]["name"] == "catalog_search"
        assert result["value"]["expected_contract_version"] == "v1"

    def test_prefers_output_tool_call_over_choices_message(self):
        """When both output[] and choices[].message.tool_calls are present, output[] is preferred."""
        response = {
            "output": [
                {
                "type": "message",
                "content": [
                    {
                        "type": "function_call",
                        "name": "catalog_search",
                        "arguments": {"query": "from_output"}
                    }
                ]
                }
            ],
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_from_choices",
                                "function": {
                                    "name": "catalog_search",
                                    "arguments": '{"query": "from_choices"}',
                                },
                                "type": "function",
                            }
                        ]
                    }
                }
            ],
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        assert result["value"]["name"] == "catalog_search"
        # Asserts precedence: the tool call from output[] wins over choices[].message.tool_calls
        assert result["value"]["arguments"]["query"] == "from_output"
        assert result["value"]["expected_contract_version"] == "v1"

    def test_uses_first_tool_call_in_list(self):
        """When multiple tool calls are present in the same list, the first one is used."""
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "first_tool",
                                    "arguments": '{"param": "first"}',
                                },
                                "type": "function",
                            },
                            {
                                "id": "call_2",
                                "function": {
                                    "name": "second_tool",
                                    "arguments": '{"param": "second"}',
                                },
                                "type": "function",
                            },
                        ]
                    }
                }
            ]
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        # Asserts stable ordering: the first tool call in the list is selected.
        assert result["value"]["name"] == "first_tool"
        assert result["value"]["arguments"]["param"] == "first"
        assert result["value"]["expected_contract_version"] == "v1"

    def test_extracts_tool_call_from_choices_message(self):
        """Chat Completions tool calls in choices[].message.tool_calls are supported."""
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_3",
                                "function": {
                                    "name": "bom_calculate",
                                    "arguments": {"product_family": "ISODEC"}
                                }
                            }
                        ]
                    }
                }
            ]
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        assert result["value"]["name"] == "bom_calculate"

    def test_handles_malformed_tool_call_arguments_string(self):
        """Malformed JSON tool-call arguments are wrapped in a raw field."""
        malformed_args = "not valid json{"
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_4",
                                "function": {
                                    "name": "bom_calculate",
                                    "arguments": malformed_args,
                                },
                            }
                        ]
                    }
                }
            ]
        }
        result = extract_primary_output(response)
        assert result["type"] == "tool_call"
        assert result["value"]["name"] == "bom_calculate"
        assert result["value"]["arguments"] == {"raw": malformed_args}
        assert result["value"]["expected_contract_version"] == "v1"
    def test_returns_unknown_with_diagnostic(self):
        """Test that unknown type with diagnostic is returned when no content."""
        response = {"id": "123", "model": "gpt-4"}
        result = extract_primary_output(response)
        assert result["type"] == "unknown"
        assert result["value"] is None
        assert "diagnostic" in result
        assert result["diagnostic"].startswith("[no text content;")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
