# KB Self-Learning Tests

## Running Tests

Run tests from the repository root:

```bash
# Run all kb_self_learning tests
pytest kb_self_learning/tests/ -v

# Run specific test file
pytest kb_self_learning/tests/test_kb_writer_service.py -v
pytest kb_self_learning/tests/test_approval_workflow.py -v

# Run with coverage
pytest kb_self_learning/tests/ -v --cov=kb_self_learning --cov-report=term-missing
```

## Test Structure

- `test_kb_writer_service.py`: Tests for KB entry submission, approval, and retrieval endpoints
- `test_approval_workflow.py`: Tests for approval workflow logic and state management

## Test Dependencies

Tests require:
- pytest
- pytest-asyncio
- fastapi
- httpx (for TestClient)

Install with:
```bash
pip install pytest pytest-asyncio fastapi httpx
```

## Known Limitations

These tests validate the API interface and basic functionality. However, the current implementation has architectural limitations that are not addressed by these tests:

1. **In-memory State**: Workflow state is not persisted to database
2. **No Authentication**: Endpoints lack authentication/authorization
3. **Stub Implementations**: Some endpoints return empty/stub data
4. **Single Instance**: Not compatible with Kubernetes multi-replica deployments

See `../ARCHITECTURAL_LIMITATIONS.md` for details.
