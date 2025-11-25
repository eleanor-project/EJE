#!/usr/bin/env python3
"""
Rebrand ELEANOR codebase from EJE to EJC with new MIF/RBJA terminology
"""

import os
import re
from pathlib import Path

# Define all replacements (order matters for some)
REPLACEMENTS = [
    # Import statements
    (r'from eje\.', 'from ejc.'),
    (r'import eje\.', 'import ejc.'),
    (r'from \.precedent_manager import JurisprudenceRepository', 'from .jurisprudence_repository import JurisprudenceRepository'),
    (r'from \.ethical_reasoning_engine import EthicalReasoningEngine', 'from .ethical_reasoning_engine import EthicalReasoningEngine'),

    # Class names
    (r'\bDecisionEngine\b', 'EthicalReasoningEngine'),
    (r'\bPrecedentManager\b', 'JurisprudenceRepository'),

    # Logger names
    (r'"EJE\.', '"EJC.'),
    (r'get_logger\("EJE"', 'get_logger("EJC"'),

    # Terminology in docstrings and comments
    (r'Ethics Jurisprudence Engine \(EJE\)', 'Ethical Jurisprudence Core (EJC)\n    Part of the Mutual Intelligence Framework (MIF)'),
    (r'Mutual Intelligence Framework (MIF)', 'Mutual Intelligence Framework (MIF)'),
    (r'rights-based safeguards', 'rights-based safeguards'),
    (r'Rights-based safeguards', 'Rights-based safeguards'),
    (r'ethical deliberation system', 'ethical deliberation system'),
    (r'Ethical deliberation system', 'Ethical deliberation system'),
    (r'Ethical Deliberation System', 'Ethical Deliberation System'),
    (r'ethical reasoning engine', 'ethical reasoning engine'),
    (r'Ethical reasoning engine', 'Ethical reasoning engine'),
    (r'jurisprudence repository', 'jurisprudence repository'),
    (r'Jurisprudence repository', 'Jurisprudence repository'),
    (r'Jurisprudence Repository', 'Jurisprudence Repository'),

    # Variable/function names
    (r'ethical_reasoning_engine', 'ethical_reasoning_engine'),
    (r'ethical_deliberation_system', 'ethical_deliberation_system'),
    (r'jurisprudence_repository', 'jurisprudence_repository'),

    # Comments referencing old terms
    (r'# EJC:', '# EJC:'),
    (r'# Ethical Jurisprudence Core', '# Ethical Jurisprudence Core'),
]

def should_process_file(filepath):
    """Check if file should be processed"""
    # Skip certain directories and files
    skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
    skip_extensions = {'.pyc', '.pyo', '.so', '.dylib', '.egg-info'}

    path = Path(filepath)

    # Check if any parent directory should be skipped
    for parent in path.parents:
        if parent.name in skip_dirs:
            return False

    # Check file extension
    if path.suffix in skip_extensions:
        return False

    # Only process text files
    valid_extensions = {'.py', '.yaml', '.yml', '.md', '.txt', '.sh', '.ini', '.cfg', '.json'}
    if path.suffix not in valid_extensions:
        return False

    return True

def rebrand_file(filepath):
    """Apply all rebranding replacements to a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Apply all replacements
        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)

        # Only write if content changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"  ❌ Error processing {filepath}: {e}")
        return False

def main():
    """Main rebranding function"""
    print("=" * 60)
    print("EJE → EJC Rebranding Script")
    print("Mutual Intelligence Framework (MIF) Terminology Update")
    print("=" * 60)
    print()

    project_root = Path("/home/user/EJE")
    files_processed = 0
    files_modified = 0

    # Walk through all files
    for root, dirs, files in os.walk(project_root):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            filepath = os.path.join(root, file)

            if should_process_file(filepath):
                files_processed += 1

                if rebrand_file(filepath):
                    files_modified += 1
                    # Show relative path
                    rel_path = os.path.relpath(filepath, project_root)
                    print(f"  ✅ Updated: {rel_path}")

    print()
    print("=" * 60)
    print(f"Rebranding complete!")
    print(f"  Files processed: {files_processed}")
    print(f"  Files modified: {files_modified}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Review changes: git diff")
    print("  2. Run tests: pytest")
    print("  3. Commit: git commit -m 'refactor: Rebrand EJE → EJC with MIF/RBJA terminology'")

if __name__ == "__main__":
    main()
