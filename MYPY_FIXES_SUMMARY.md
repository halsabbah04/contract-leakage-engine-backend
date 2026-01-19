# MyPy Type Checking Fixes Summary

## Fixes Applied ✅

1. **text_preprocessing_service.py**
   - ✅ Line 95: Added type annotation `current_segment: list[str] = []`
   - ✅ Line 184: Changed `any` to `Any` in return type
   - ✅ Line 219: Wrapped division in `float()` to match type
   - ✅ Added `Any` to imports

2. **finding.py**
   - ✅ Lines 97-98: Fixed `default_factory` to use lambda for Pydantic model defaults

3. **clause.py**
   - ✅ Line 72: Fixed `default_factory` to use lambda for Pydantic model

4. **contract.py**
   - ✅ Added missing `upload_date` field
   - ✅ Added missing `clause_ids` field
   - ✅ Added `List` to imports

5. **report_service.py**
   - ✅ Line 686: Added type annotation for `counts` variable

## Remaining Issues (Require Manual Review)

### Optional Arguments in Pydantic Models

Many mypy errors are about "missing named arguments" for optional fields. These occur because:
- Pydantic models have optional fields with `None` defaults
- MyPy strict mode expects all arguments to be explicitly passed

**Files affected:**
- `rules_engine.py` (lines 239, 311, 316)
- `ai_detection_service.py` (lines 269, 277, 280)
- `nlp_service.py` (lines 209, 420)
- `clause_extraction_service.py` (line 118)
- `session_repository.py` (line 66)

**Solutions:**
1. Explicitly pass optional arguments with `None` or `=None` in model instantiation
2. Use `# type: ignore[call-arg]` for known safe calls
3. Configure mypy to be less strict with Pydantic models

### Specific Fixes Needed

#### rules_engine.py (Line 239)
```python
# Current - missing optional args
finding = LeakageFinding(
    id=...,
    # missing: embedding=None, user_notes=None
)

# Fix - add optional args explicitly
finding = LeakageFinding(
    id=...,
    embedding=None,
    user_notes=None
)
```

#### nlp_service.py (Line 268)
```python
# Issue: max() key argument type mismatch
best_type = max(type_scores, key=type_scores.get)  # type: ignore[arg-type]
```

### Type Stub Missing
- `yaml` module needs `types-PyYAML` package
- Run: `python -m pip install types-PyYAML`

### Unchecked Function Bodies
- `cosmos_client.py` lines 27-29 need return type annotations
- Add `-> CosmosClient`, `-> DatabaseProxy`, `-> ContainerProxy`

## Recommendation

For a POC/MVP project:
1. Install `types-PyYAML` for yaml stubs
2. Add `# type: ignore` comments for known-safe Pydantic model instantiations
3. Consider adding to `pyproject.toml`:
```toml
[tool.mypy]
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

This will make mypy work better with Pydantic models and reduce false positives.
