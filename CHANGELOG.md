# Changelog

All notable changes to the Ethical Jurisprudence Core (EJC)
    Part of the Mutual Intelligence Framework (MIF) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-11-25

### Added

#### Type Hints Infrastructure
- ✅ Added comprehensive type hints to all core modules
  - `ethical_reasoning_engine.py`: Full type annotations for EthicalReasoningEngine class
  - `precedent_manager.py`: Type hints for JurisprudenceRepository
  - `precedent_manager_sqlite.py`: Type hints for SQLite implementation
  - `aggregator.py`: Type annotations for aggregation logic
  - `base_critic.py`: Type hints for critic base class
  - `validation.py`: Type hints for validation functions

#### SQLite Migration for Precedents
- ✅ **New SQLite-based precedent storage system** (`precedent_manager_sqlite.py`)
  - Structured relational database schema
  - Improved query performance
  - Better data integrity
  - Support for complex queries
  - Foreign key relationships
  - Indexed lookups for fast retrieval

- ✅ **Database schema** (`precedent_schema.py`)
  - `precedents` table: Core precedent data
  - `critic_outputs` table: Individual critic evaluations
  - `precedent_embeddings` table: Semantic embeddings
  - `precedent_references` table: Similarity relationships

- ✅ **Migration script** (`scripts/migrate_precedents.py`)
  - Convert existing JSON precedents to SQLite
  - Automatic backup of original data
  - Command-line interface
  - Schema creation tool

#### Enhanced Dashboard
- ✅ **Modern web dashboard** (`server/dashboard_enhanced.py`)
  - Real-time metrics and analytics
  - Beautiful dark-themed UI
  - Live decision monitoring
  - Critic performance statistics
  - Precedent browsing
  - Auto-refresh every 30 seconds

- **New API endpoints:**
  - `/api/statistics` - Overall system statistics
  - `/api/recent-decisions` - Recent decision history
  - `/api/critic-stats` - Per-critic performance metrics
  - `/api/precedent/<hash>` - Individual precedent lookup

#### Performance Benchmarks
- ✅ **Comprehensive benchmark suite** (`benchmarks/performance_benchmarks.py`)
  - Single decision latency measurement
  - Throughput testing (decisions/second)
  - Cache hit rate analysis
  - Precedent lookup performance
  - Embedding generation speed
  - Parallel critic execution timing
  - JSON export of results

#### CI/CD Pipeline
- ✅ **GitHub Actions workflows**
  - `.github/workflows/ci.yml` - Main CI pipeline
    - Multi-version Python testing (3.9, 3.10, 3.11)
    - Code coverage with Codecov
    - Linting with Ruff
    - Type checking with mypy
    - Security scanning with Bandit
    - Automated benchmarks
    - Docker image builds
    - Documentation builds

  - `.github/workflows/release.yml` - Release automation
    - PyPI publishing
    - Docker Hub publishing
    - Version tagging

- ✅ **Enhanced pytest configuration** (`pytest.ini`)
  - Test markers (unit, integration, slow, benchmark)
  - Coverage configuration
  - Strict mode enforcement

- ✅ **Project metadata** (`pyproject.toml`)
  - Modern Python packaging
  - Dependency management
  - Tool configurations (black, ruff, mypy, isort)
  - Development dependencies

### Improved

- **Code Quality**
  - Type safety throughout the codebase
  - Better error handling
  - Improved documentation

- **Performance**
  - SQLite database for faster precedent lookups
  - Indexed database queries
  - Optimized embedding storage

- **Developer Experience**
  - Automated testing and benchmarking
  - Continuous integration
  - Code quality checks
  - Standardized formatting

### Technical Details

**Database Schema:**
```sql
precedents (
    id, case_hash, request_id, timestamp,
    input_text, input_context, input_metadata,
    final_verdict, final_reason, avg_confidence, ambiguity
)

critic_outputs (
    id, precedent_id, critic_name, verdict,
    confidence, justification, weight, priority
)

precedent_embeddings (
    id, precedent_id, embedding, model_name
)

precedent_references (
    id, precedent_id, referenced_precedent_id,
    similarity_score, reference_type
)
```

**Migration Path:**
1. Run `python scripts/migrate_precedents.py` to convert JSON to SQLite
2. Update imports to use `PrecedentManagerSQLite`
3. Existing JSON data is automatically backed up

**Benchmark Metrics:**
- Decision latency (mean, median, min, max, stdev)
- Throughput (decisions/second)
- Cache performance (hit rate, lookup time)
- Precedent lookup speed
- Embedding generation time
- Parallel execution efficiency

### Migration Guide

**For existing installations:**

1. Install updated dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Migrate precedent data to SQLite:
   ```bash
   python scripts/migrate_precedents.py
   ```

3. (Optional) Update code to use SQLite manager:
   ```python
   from ejc.core.precedent_manager_sqlite import PrecedentManagerSQLite
   pm = PrecedentManagerSQLite("./eleanor_data/precedents.db")
   ```

4. Launch enhanced dashboard:
   ```bash
   python -m eje.server.dashboard_enhanced
   ```

5. Run benchmarks:
   ```bash
   python benchmarks/performance_benchmarks.py
   ```

### Backward Compatibility

- JSON-based JurisprudenceRepository still available
- Migration is optional but recommended
- All existing APIs remain unchanged
- Configuration format unchanged

---

## [1.2.0] - Previous Release

See git history for previous changes.
