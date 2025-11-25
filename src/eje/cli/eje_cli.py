#!/usr/bin/env python3
"""
Enhanced CLI for the Ethics Jurisprudence Engine (EJE)
Provides multiple commands for evaluation, precedent management, and system inspection.
"""

import click
import json
import sys
from tabulate import tabulate
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from eje.core.decision_engine import DecisionEngine
from eje.core.precedent_manager import PrecedentManager
from eje.core.audit_log import AuditLogger, AuditEvent
from eje.core.config_loader import load_global_config


@click.group()
@click.version_option(version="1.2.0")
def cli():
    """Ethics Jurisprudence Engine (EJE) - Command Line Interface"""
    pass


@cli.command()
@click.option('--case', required=True, help='Case JSON string or file path')
@click.option('--config', default='config/global.yaml', help='Config file path')
@click.option('--pretty', is_flag=True, help='Pretty print output')
def evaluate(case, config, pretty):
    """Evaluate a case using configured critics"""
    try:
        # Load case from file or parse JSON
        if case.startswith('@'):
            # Load from file
            with open(case[1:], 'r') as f:
                case_data = json.load(f)
        else:
            case_data = json.loads(case)

        # Initialize engine
        click.echo("🔧 Initializing Decision Engine...")
        engine = DecisionEngine(config)

        # Evaluate
        click.echo(f"⚖️  Evaluating case...")
        result = engine.evaluate(case_data)

        # Display results
        click.echo("\n" + "="*60)
        click.echo(f"📋 DECISION: {result['final_decision']['overall_verdict']}")
        click.echo(f"🎯 Confidence: {result['final_decision']['avg_confidence']:.2%}")
        click.echo(f"🆔 Request ID: {result['request_id']}")
        click.echo("="*60)

        # Critic outputs
        click.echo("\n👥 Critic Outputs:")
        critic_table = []
        for output in result['critic_outputs']:
            critic_table.append([
                output['critic'],
                output['verdict'],
                f"{output['confidence']:.2%}",
                output['justification'][:50] + "..." if len(output['justification']) > 50 else output['justification']
            ])

        click.echo(tabulate(critic_table,
                           headers=['Critic', 'Verdict', 'Confidence', 'Justification'],
                           tablefmt='grid'))

        # Precedent references
        if result['precedent_refs']:
            click.echo(f"\n📚 Found {len(result['precedent_refs'])} similar precedent(s)")

        # Full JSON output if requested
        if pretty:
            click.echo("\n📄 Full JSON Output:")
            click.echo(json.dumps(result, indent=2))

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def precedents():
    """Manage precedent database"""
    pass


@precedents.command('list')
@click.option('--limit', default=10, help='Maximum number of precedents to show')
@click.option('--config', default='config/global.yaml', help='Config file path')
def list_precedents(limit, config):
    """List stored precedents"""
    try:
        cfg = load_global_config(config)
        pm = PrecedentManager(cfg.get('data_path', './eleanor_data'))

        with open(pm.store_path, 'r') as f:
            precedents = json.load(f)

        if not precedents:
            click.echo("📚 No precedents stored yet")
            return

        click.echo(f"📚 Total Precedents: {len(precedents)}\n")

        table = []
        for i, p in enumerate(precedents[-limit:]):
            table.append([
                i + 1,
                p.get('timestamp', 'N/A')[:19],
                p.get('final_decision', {}).get('overall_verdict', 'N/A'),
                f"{p.get('final_decision', {}).get('avg_confidence', 0):.2%}",
                p.get('request_id', 'N/A')[:8]
            ])

        click.echo(tabulate(table,
                           headers=['#', 'Timestamp', 'Verdict', 'Confidence', 'Request ID'],
                           tablefmt='grid'))

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@precedents.command('search')
@click.option('--query', required=True, help='Search query text')
@click.option('--threshold', default=0.8, type=float, help='Similarity threshold (0-1)')
@click.option('--config', default='config/global.yaml', help='Config file path')
def search_precedents(query, threshold, config):
    """Search for similar precedents using semantic similarity"""
    try:
        cfg = load_global_config(config)
        pm = PrecedentManager(cfg.get('data_path', './eleanor_data'))

        # Search
        click.echo(f"🔍 Searching for precedents similar to: '{query}'")
        results = pm.lookup({'text': query}, similarity_threshold=threshold)

        if not results:
            click.echo(f"❌ No precedents found with similarity >= {threshold}")
            return

        click.echo(f"\n✅ Found {len(results)} similar precedent(s):\n")

        for i, p in enumerate(results, 1):
            sim_score = p.get('similarity_score', 1.0)
            click.echo(f"\n{'='*60}")
            click.echo(f"Match #{i} - Similarity: {sim_score:.2%}")
            click.echo(f"{'='*60}")
            click.echo(f"Request ID: {p.get('request_id')}")
            click.echo(f"Timestamp: {p.get('timestamp')}")
            click.echo(f"Verdict: {p.get('final_decision', {}).get('overall_verdict')}")
            click.echo(f"Confidence: {p.get('final_decision', {}).get('avg_confidence', 0):.2%}")
            click.echo(f"Input: {p.get('input', {}).get('text', 'N/A')[:100]}...")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@precedents.command('stats')
@click.option('--config', default='config/global.yaml', help='Config file path')
def precedent_stats(config):
    """Show precedent database statistics"""
    try:
        cfg = load_global_config(config)
        pm = PrecedentManager(cfg.get('data_path', './eleanor_data'))

        stats = pm.get_statistics()

        click.echo("\n📊 Precedent Database Statistics\n")
        click.echo(f"Total Precedents: {stats['total_precedents']}")
        click.echo(f"Embeddings Cached: {stats['embeddings_cached']}")
        click.echo(f"Semantic Search: {'✅ Enabled' if stats['embeddings_enabled'] else '❌ Disabled'}")
        click.echo(f"Storage Path: {stats['storage_path']}\n")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def critics():
    """Manage and inspect critics"""
    pass


@critics.command('list')
@click.option('--config', default='config/global.yaml', help='Config file path')
def list_critics(config):
    """List all loaded critics"""
    try:
        cfg = load_global_config(config)

        click.echo("\n👥 Configured Critics:\n")

        # Official critics
        click.echo("Official Critics:")
        official = ['OpenAI', 'Anthropic', 'Gemini']
        for name in official:
            click.echo(f"  ✓ {name}")

        # Plugin critics
        plugins = cfg.get('plugin_critics', [])
        if plugins:
            click.echo("\nPlugin Critics:")
            for plugin in plugins:
                click.echo(f"  ✓ {plugin}")

        # Weights
        click.echo("\n⚖️  Critic Weights:")
        weights = cfg.get('critic_weights', {})
        for name, weight in weights.items():
            click.echo(f"  {name}: {weight}")

        # Priorities
        priorities = cfg.get('critic_priorities', {})
        if priorities:
            click.echo("\n🔒 Priority Overrides:")
            for name, priority in priorities.items():
                click.echo(f"  {name}: {priority}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def audit():
    """Query audit logs"""
    pass


@audit.command('query')
@click.option('--verdict', help='Filter by verdict (ALLOW/DENY/REVIEW/BLOCK)')
@click.option('--limit', default=10, help='Maximum number of records')
@click.option('--config', default='config/global.yaml', help='Config file path')
def query_audit(verdict, limit, config):
    """Query audit log entries"""
    try:
        cfg = load_global_config(config)
        logger = AuditLogger(cfg.get('db_uri'))

        session = logger.Session()

        # Build query
        query = session.query(AuditEvent)

        if verdict:
            query = query.filter(AuditEvent.verdict == verdict.upper())

        # Execute
        results = query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()

        if not results:
            click.echo("📋 No audit log entries found")
            session.close()
            return

        click.echo(f"\n📋 Audit Log Entries (showing {len(results)}):\n")

        table = []
        for event in results:
            table.append([
                event.id,
                str(event.timestamp)[:19],
                event.verdict,
                event.prompt[:30] + "..." if len(event.prompt) > 30 else event.prompt
            ])

        click.echo(tabulate(table,
                           headers=['ID', 'Timestamp', 'Verdict', 'Prompt'],
                           tablefmt='grid'))

        session.close()

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', default='config/global.yaml', help='Config file path')
def validate_config(config):
    """Validate configuration file"""
    try:
        click.echo(f"🔍 Validating configuration: {config}")

        cfg = load_global_config(config)

        # Check required fields
        required = ['llm', 'critic_weights', 'block_threshold']
        missing = [field for field in required if field not in cfg]

        if missing:
            click.echo(f"❌ Missing required fields: {', '.join(missing)}")
            sys.exit(1)

        # Check API keys
        api_keys = cfg.get('llm', {}).get('api_keys', {})
        for provider in ['openai', 'anthropic', 'gemini']:
            if not api_keys.get(provider):
                click.echo(f"⚠️  Warning: No API key for {provider}")

        click.echo("✅ Configuration is valid")

    except Exception as e:
        click.echo(f"❌ Configuration error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', default='config/global.yaml', help='Config file path')
def show_config(config):
    """Display current configuration"""
    try:
        cfg = load_global_config(config)

        click.echo("\n⚙️  Current Configuration:\n")
        click.echo(json.dumps(cfg, indent=2, default=str))

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', default='config/global.yaml', help='Config file path')
def stats(config):
    """Show system statistics (cache, precedents, performance)"""
    try:
        click.echo("\n📊 EJE System Statistics\n")
        click.echo("="*60)

        # Load configuration
        cfg = load_global_config(config)

        # Precedent stats
        pm = PrecedentManager(cfg.get('data_path', './eleanor_data'))
        prec_stats = pm.get_statistics()

        click.echo("\n📚 Precedent Database:")
        click.echo(f"  Total Precedents: {prec_stats['total_precedents']}")
        click.echo(f"  Embeddings Cached: {prec_stats['embeddings_cached']}")
        click.echo(f"  Semantic Search: {'✅ Enabled' if prec_stats['embeddings_enabled'] else '❌ Disabled'}")

        # Configuration stats
        click.echo("\n⚙️  Configuration:")
        click.echo(f"  Max Parallel Calls: {cfg.get('max_parallel_calls', 5)}")
        click.echo(f"  Retrain Batch Size: {cfg.get('retrain_batch_size', 25)}")
        click.echo(f"  Cache Enabled: {'✅ Yes' if cfg.get('enable_cache', True) else '❌ No'}")
        click.echo(f"  Cache Size: {cfg.get('cache_size', 1000)}")
        click.echo(f"  Block Threshold: {cfg.get('block_threshold', 0.5)}")

        # Audit log stats
        audit = AuditLogger(cfg.get('db_uri'))
        session = audit.Session()
        total_decisions = session.query(AuditEvent).count()

        click.echo("\n📋 Audit Log:")
        click.echo(f"  Total Decisions: {total_decisions}")

        # Verdict breakdown
        if total_decisions > 0:
            verdicts = session.query(AuditEvent.verdict,
                                    session.query(AuditEvent).filter_by().count())\
                             .group_by(AuditEvent.verdict).all()

            click.echo("\n  Verdict Breakdown:")
            for verdict, count in verdicts:
                percentage = (count / total_decisions) * 100
                click.echo(f"    {verdict}: {count} ({percentage:.1f}%)")

        session.close()

        click.echo("\n" + "="*60 + "\n")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
