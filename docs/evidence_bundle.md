# Evidence Bundle Schema

`schemas/evidence_bundle.json` defines the atomic unit emitted by each critic so downstream aggregators can reason over consistent, structured data.

## Top-level fields
- **schema_version**: Semantic version for the bundle schema (e.g., `v1.0.0`).
- **bundle_id**: UUID identifying a specific bundle instance.
- **metadata**: Provenance about the critic run (critic identity/version, timestamp, config version, run ID, optional environment details).
- **input_snapshot**: Immutable view of the prompt plus optional context, precedents, and attachments provided to the critic.
- **critic_output**: Normalized verdict and supporting findings, including confidence, optional severity, recommended actions, and labels.
- **justification**: Summary, supporting evidence, and optional reasoning trace and uncertainties linking findings to the verdict.

## Validation highlights
- Required text fields include minimum lengths to prevent empty strings (e.g., critic name/version, prompts, recommended actions, labels, finding codes/descriptions, evidence content, and reasoning step descriptions).
- Evidence sources are normalized to one of `input`, `knowledge_base`, `policy`, `precedent_id`, or `system` to improve downstream routing.
- Arrays such as findings and supporting evidence enforce at least one item; URIs and UUIDs use standard JSON Schema formats.

## Usage
1. Update bundles to include the required fields above before validation.
2. Validate bundles with any Draft-07 JSON Schema validator against `schemas/evidence_bundle.json`.
3. Include the schema version and critic configuration version to aid debugging when schema or critic definitions evolve.
