"""
CLI tool for running EJC adversarial tests.

Usage:
    python -m ejc.testing.cli --help
    python -m ejc.testing.cli run-all
    python -m ejc.testing.cli run-suite prompt_injection
    python -m ejc.testing.cli run-critical
"""

import argparse
import sys
import logging
from pathlib import Path

from .runner import TestRunner, run_all_tests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="EJC Adversarial Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python -m ejc.testing.cli run-all

  # Run specific suite
  python -m ejc.testing.cli run-suite prompt_injection

  # Run only critical tests
  python -m ejc.testing.cli run-critical

  # Generate JSON report
  python -m ejc.testing.cli run-all --format json --output results.json

  # List available suites
  python -m ejc.testing.cli list-suites
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Run all tests
    run_all_parser = subparsers.add_parser(
        'run-all',
        help='Run all test suites'
    )
    run_all_parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Path to save report'
    )
    run_all_parser.add_argument(
        '--format', '-f',
        choices=['text', 'json'],
        default='text',
        help='Report format'
    )

    # Run specific suite
    run_suite_parser = subparsers.add_parser(
        'run-suite',
        help='Run a specific test suite'
    )
    run_suite_parser.add_argument(
        'suite',
        choices=[
            'prompt_injection',
            'bias_probe',
            'context_poisoning',
            'malformed_input',
            'boundary'
        ],
        help='Suite to run'
    )
    run_suite_parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Path to save report'
    )

    # Run critical tests only
    run_critical_parser = subparsers.add_parser(
        'run-critical',
        help='Run only critical severity tests'
    )
    run_critical_parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Path to save report'
    )

    # List suites
    subparsers.add_parser(
        'list-suites',
        help='List available test suites'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == 'list-suites':
        return list_suites()
    elif args.command == 'run-all':
        return run_all_command(args)
    elif args.command == 'run-suite':
        return run_suite_command(args)
    elif args.command == 'run-critical':
        return run_critical_command(args)


def list_suites():
    """List available test suites."""
    suites = [
        ("Prompt Injection Suite", "Tests for prompt injection attacks (CRITICAL)"),
        ("Bias Probe Suite", "Tests for systematic bias (HIGH)"),
        ("Context Poisoning Suite", "Tests for context manipulation (MEDIUM)"),
        ("Malformed Input Suite", "Tests for malformed input handling (MEDIUM)"),
        ("Boundary Suite", "Tests for boundary conditions (LOW)"),
    ]

    print("\nAvailable Test Suites:\n")
    for name, description in suites:
        print(f"  {name}")
        print(f"    {description}\n")

    return 0


def run_all_command(args):
    """Run all tests command."""
    print("\n" + "="*80)
    print("EJC ADVERSARIAL TEST SUITE - RUNNING ALL TESTS")
    print("="*80 + "\n")

    try:
        # Note: In real usage, user would provide EJC instance
        # For CLI, we run in mock mode without actual EJC
        print("⚠️  WARNING: Running without EJC instance (tests will use mock mode)")
        print("   For real testing, use the Python API with your EJC instance\n")

        results = run_all_tests(
            ejc_instance=None,
            output_path=args.output,
            format=args.format,
        )

        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Pass Rate: {results['passed']/results['total_tests']*100:.1f}%")

        if args.output:
            print(f"\nFull report saved to: {args.output}")

        # Return exit code based on failures
        return 0 if results['failed'] == 0 else 1

    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        return 1


def run_suite_command(args):
    """Run specific suite command."""
    print(f"\nRunning suite: {args.suite}\n")

    try:
        print("⚠️  WARNING: Running without EJC instance (tests will use mock mode)")
        print("   For real testing, use the Python API with your EJC instance\n")

        runner = TestRunner(ejc_instance=None)
        results = runner.run_suite(args.suite)

        # Print results
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        print(f"\nSuite Results:")
        print(f"  Passed: {passed}/{len(results)}")
        print(f"  Failed: {failed}/{len(results)}")

        if failed > 0:
            print("\nFailed Tests:")
            for r in results:
                if not r.passed:
                    print(f"  - {r.test_name}: {r.message}")

        return 0 if failed == 0 else 1

    except Exception as e:
        print(f"\n❌ Error running suite: {e}")
        import traceback
        traceback.print_exc()
        return 1


def run_critical_command(args):
    """Run critical tests command."""
    print("\n" + "="*80)
    print("RUNNING CRITICAL SEVERITY TESTS ONLY")
    print("="*80 + "\n")

    try:
        print("⚠️  WARNING: Running without EJC instance (tests will use mock mode)\n")

        runner = TestRunner(ejc_instance=None)
        results = runner.run_critical_only()

        # Print summary
        print("\nCritical Tests Summary:")
        print(f"Total: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")

        return 0 if results['failed'] == 0 else 1

    except Exception as e:
        print(f"\n❌ Error running critical tests: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
