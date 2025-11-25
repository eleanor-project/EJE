#!/usr/bin/env python3
"""
Ethical Jurisprudence Core (EJC)
Part of the Mutual Intelligence Framework (MIF)

Simple CLI runner for the ethical reasoning engine.
"""

import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ejc.core.ethical_reasoning_engine import EthicalReasoningEngine


def main():
    """Main runner for EJC ethical reasoning engine"""
    parser = argparse.ArgumentParser(
        description="Run Ethical Jurisprudence Core (EJC) - Mutual Intelligence Framework"
    )
    parser.add_argument(
        '--config',
        default='config/global.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--case',
        required=False,
        help='Case JSON string or @file path'
    )

    args = parser.parse_args()

    # Initialize engine
    print("🔧 Initializing Ethical Reasoning Engine (MIF/RBJA)...")
    engine = EthicalReasoningEngine(args.config)

    if args.case:
        # Load case
        if args.case.startswith('@'):
            with open(args.case[1:], 'r') as f:
                case_data = json.load(f)
        else:
            case_data = json.loads(args.case)

        # Evaluate
        print(f"⚖️  Evaluating case...")
        result = engine.evaluate(case_data)

        # Display results
        print("\n" + "=" * 60)
        print("ETHICAL REASONING RESULT")
        print("=" * 60)
        print(f"Request ID: {result['request_id']}")
        print(f"Timestamp: {result['timestamp']}")
        print(f"\nFinal Decision: {result['final_decision']['overall_verdict']}")
        print(f"Confidence: {result['final_decision'].get('avg_confidence', 'N/A')}")

        if 'reason' in result['final_decision']:
            print(f"\nReason: {result['final_decision']['reason']}")

        if 'precedent_refs' in result and result['precedent_refs']:
            print(f"\nPrecedents Referenced: {len(result['precedent_refs'])}")

        print("\n" + "=" * 60)
        print("ETHICAL DELIBERATION SYSTEM OUTPUT")
        print("=" * 60)
        for critic_out in result['critic_outputs']:
            print(f"\n{critic_out['critic']}:")
            print(f"  Verdict: {critic_out['verdict']}")
            print(f"  Confidence: {critic_out['confidence']}")
            print(f"  Justification: {critic_out['justification'][:100]}...")

        print("\n✅ Evaluation complete")
    else:
        print("No case provided. Use --case flag.")
        print("\nExample:")
        print('  python -m ejc.cli.run_engine --case \'{"text":"Test case"}\'')


if __name__ == "__main__":
    main()
