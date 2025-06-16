# Component-Level Debugging Task Recommendations

## Post-Infrastructure-Fix Status
✅ **Infrastructure Resolved**: All 222 tests now execute in 4.63 seconds (no timeouts)
🔍 **Logical Failures**: 95 failures requiring systematic debugging across 7 modules
📊 **Pass Rate**: 57.2% (127/222 tests passing)

## Phase 1: Quick Wins (Parallel Execution - Low Risk)

### Task 1A: Fix Scraper Component Missing Method
**Module**: `src/webdeface/scraper/extractor.py`
**Issue**: `ContentExtractor` missing `_get_soup` method
**Impact**: LOW | **Effort**: LOW | **Tests Affected**: 1
**Fix**: Add missing `_get_soup` method implementation to ContentExtractor class
**Dependencies**: None
**Validation**: `pytest tests/test_scraper_components.py::TestContentExtractor::test_text_block_extraction -v`

### Task 1B: Fix Scheduler Configuration Missing Attribute
**Module**: `src/webdeface/config/settings.py`
**Issue**: `AppSettings` missing `database_url` attribute
**Impact**: LOW | **Effort**: LOW | **Tests Affected**: 1
**Fix**: Add `database_url` field to AppSettings class
**Dependencies**: None
**Validation**: `pytest tests/test_scheduler_components.py::TestSchedulerManager::test_scheduler_manager_setup -v`

### Task 1C: Fix Classifier Function Signature Mismatch
**Module**: `src/webdeface/classifier/feedback.py`
**Issue**: `FeedbackCollector.submit_false_positive_feedback()` unexpected `snapshot_id` parameter
**Impact**: MEDIUM | **Effort**: LOW | **Tests Affected**: 1
**Fix**: Update method signature to accept `snapshot_id` parameter
**Dependencies**: None
**Validation**: `pytest tests/test_classifier_components.py::TestFeedbackCollector::test_submit_false_positive_feedback -v`

## Phase 2: Framework Stabilization (Sequential - Medium Risk)

### Task 2A: Fix Async/Sync Test Framework Configuration
**Modules**: `tests/test_slack_infrastructure.py`, `tests/test_storage_infrastructure.py`
**Issue**: Async functions marked but not properly configured for pytest-asyncio
**Impact**: HIGH | **Effort**: MEDIUM | **Tests Affected**: 17
**Fix**:
- Remove incorrect `@pytest.mark.asyncio` decorators from sync functions
- Fix async fixture configuration in conftest.py
- Update pytest configuration for proper async/sync handling
**Dependencies**: pytest-asyncio configuration
**Validation**: `pytest tests/test_slack_infrastructure.py tests/test_storage_infrastructure.py -v`

### Task 2B: Fix Model Assertion Logic
**Module**: `tests/test_storage_infrastructure.py`
**Issue**: SQLAlchemy model creation tests with incorrect assertion logic
**Impact**: MEDIUM | **Effort**: LOW | **Tests Affected**: 3
**Fix**: Update assertion logic for model attribute validation
**Dependencies**: Task 2A completion
**Validation**: `pytest tests/test_storage_infrastructure.py::TestSQLAlchemyModels -v`

## Phase 3: Critical System Debugging (Sequential - High Priority)

### Task 3A: Debug API Authentication System
**Module**: `src/webdeface/api/auth.py`, `src/webdeface/api/middleware.py`
**Issue**: All protected API endpoints returning 401 instead of expected responses
**Impact**: CRITICAL | **Effort**: HIGH | **Tests Affected**: 38
**Root Cause Analysis Required**:
- Token verification logic malfunction
- Authentication middleware not properly configured
- Token generation/validation mismatch
**Dependencies**: None (isolated system)
**Validation**: `pytest tests/test_api_interface.py::TestAuthenticationAPI -v`
**Follow-up**: Once auth fixed, re-run all API tests

### Task 3B: Debug CLI Command Execution Framework
**Module**: `src/webdeface/cli/main.py`, `src/webdeface/cli/commands/`
**Issue**: All CLI commands returning exit code 2 instead of 0
**Impact**: HIGH | **Effort**: HIGH | **Tests Affected**: 14
**Root Cause Analysis Required**:
- Command routing logic failure
- Argument parsing issues
- CLI framework integration problems
**Dependencies**: None (isolated system)
**Validation**: `pytest tests/test_cli_interface.py::TestWebsiteCommands::test_website_add_success -v`

## Phase 4: Implementation Completion (Parallel - Medium Priority)

### Task 4A: Implement Missing AlertGenerator Class
**Module**: `src/webdeface/classifier/alerts.py`
**Issue**: Missing `AlertGenerator` class implementation
**Impact**: MEDIUM | **Effort**: MEDIUM | **Tests Affected**: 2
**Fix**: Create AlertGenerator class with required methods for defacement alert generation
**Dependencies**: None
**Validation**: `pytest tests/test_classifier_components.py::TestClassifierIntegration -v`

### Task 4B: Fix Content Vectorization Logic
**Module**: `src/webdeface/classifier/vectorizer.py`
**Issue**: Tuple index out of range in vectorization process
**Impact**: MEDIUM | **Effort**: MEDIUM | **Tests Affected**: 2
**Fix**: Debug vectorization logic and fix indexing errors
**Dependencies**: None
**Validation**: `pytest tests/test_classifier_components.py::TestContentVectorizer::test_vectorize_content -v`

### Task 4C: Fix Workflow Step Hash Implementation
**Module**: `src/webdeface/scheduler/workflow.py`
**Issue**: `WorkflowStep` class not hashable, preventing dependency graph building
**Impact**: LOW | **Effort**: MEDIUM | **Tests Affected**: 2
**Fix**: Implement `__hash__` and `__eq__` methods for WorkflowStep class
**Dependencies**: Task 1B completion
**Validation**: `pytest tests/test_scheduler_components.py::TestWorkflowEngine -v`

## Execution Strategy

### Recommended Approach: **MIXED PARALLEL/SEQUENTIAL**

**Parallel Track 1 (Low Risk)**:
- Task 1A: Scraper missing method
- Task 1B: Scheduler configuration
- Task 1C: Classifier function signature
- Task 4A: AlertGenerator implementation
- Task 4B: Vectorization logic
- Task 4C: Workflow step hashing

**Sequential Track 2 (Framework)**:
- Task 2A: Async/sync framework fixes
- Task 2B: Model assertion logic (depends on 2A)

**Sequential Track 3 (Critical Systems)**:
- Task 3A: API authentication debugging
- Task 3B: CLI command debugging

### Validation Gates

**After Phase 1**: Expected pass rate increase to ~65% (8 additional passing tests)
**After Phase 2**: Expected pass rate increase to ~75% (20 additional passing tests)
**After Phase 3**: Expected pass rate increase to ~95% (52 additional passing tests)
**After Phase 4**: Expected pass rate reach ~98% (remaining tests passing)

### Risk Assessment

**Low Risk**: Tasks 1A, 1B, 1C, 4A, 4C (isolated changes, clear fixes)
**Medium Risk**: Tasks 2A, 2B, 4B (framework configuration, logic debugging)
**High Risk**: Tasks 3A, 3B (complex system debugging, authentication, CLI framework)

### Dependencies Map

```
Task 1A ──┐
Task 1B ──┼─→ All can run in parallel
Task 1C ──┘

Task 2A ──→ Task 2B (framework dependency)

Task 3A ──┐
Task 3B ──┴─→ Independent critical systems

Task 4A ──┐
Task 4B ──┼─→ Can run in parallel with Phase 1
Task 4C ──┘ (depends on Task 1B for config)
```

### Monitoring Strategy

**Success Metrics**:
- Pass rate increase after each phase
- No regression in previously passing tests
- Execution time remains under 10 seconds
- No new infrastructure timeouts

**Rollback Criteria**:
- Pass rate decreases from baseline 57.2%
- Execution time exceeds 30 seconds
- Infrastructure timeouts return

This debugging plan provides clear, actionable tasks for systematic resolution of the 95 logical test failures while maintaining the resolved infrastructure stability.
