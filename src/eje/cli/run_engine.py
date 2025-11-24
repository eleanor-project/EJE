from core.config import load_global_config
from core.audit import AuditLogger
from core.aggregation import Aggregator
from core.retraining import Retrainer
from critics import openai, gemini, anthropic, base, plugin_loader
import asyncio

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run Eleanor Engine")
    parser.add_argument('--config', required=True)
    parser.add_argument('--decision', required=False)
    parser.add_argument('--dashboard', action='store_true')
    parser.add_argument('--healthcheck', action='store_true')
    args = parser.parse_args()
    config = load_global_config(args.config)
    audit = AuditLogger(config['db_uri'])
    aggregator = Aggregator(config)
    retrainer = Retrainer(config, audit)
    # Init critics
    critics = [
        base.CriticBase("OpenAI", openai.Supplier(config), config.get('critic_weights', {}).get("Rights",1), config.get('critic_priorities',{}).get("Rights")),
        base.CriticBase("Gemini", gemini.Supplier(config), config.get('critic_weights', {}).get("Equity",1), config.get('critic_priorities',{}).get("Equity")),
        base.CriticBase("Claude", anthropic.Supplier(config), config.get('critic_weights', {}).get("Utilitarian",1), config.get('critic_priorities',{}).get("Utilitarian")),
    ]
    critics += plugin_loader.load_all_plugins(config.get('plugin_critics', []))
    if args.dashboard:
        from dashboard.app import serve_dashboard
        serve_dashboard(config.get("dashboard_port", 8049))
    if args.decision:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(asyncio.gather(*[c.evaluate(args.decision,{}) for c in critics]))
        agg = aggregator.aggregate(results)
        audit.log_event(args.decision, agg, results)
        retrainer.maybe_retrain(agg,results)
        print("Aggregate:", agg['overall_verdict'])
        print("Reason:", agg['reason'])
        print("Details:", agg['details'])

if __name__ == "__main__":
    main()
