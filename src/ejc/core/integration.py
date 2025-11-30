"""
Eleanor Project: EJE Integration Layer (src/ejc/core/integration.py)

Integrates infrastructure modules (API, SDK, error handling, adversarial testing) with core engine (aggregator, audit_log, critic_loader, ethical_reasoning_engine). Provides unified interface for EJE pipeline execution and connects audit logging, error handling, and recovery mechanisms throughout.

Copyright (c) Eleanor Project, 2026.
"""

from .aggregator import Aggregator
from .audit_log import AuditLogger
from .critic_loader import CriticLoader
from .ethical_reasoning_engine import EthicalReasoningEngine
from .error_handling import CircuitBreaker, RetryableError, error_recovery

from typing import Any, Dict, List, Optional

class EJEIntegration:
    """
    Orchestrates calls between API/SDK and core EJE engine modules for pipeline execution, critic aggregation, audit logging, and error recovery.

    Args:
        config (dict): System configuration dictionary.

    Raises:
        RuntimeError: If critical components fail to initialize.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.aggregator = Aggregator(config, root_config=config)
        self.audit_logger = AuditLogger()
        self.critic_loader = CriticLoader(config)
        self.reasoning_engine = EthicalReasoningEngine(config)
        self.circuit_breaker = CircuitBreaker(max_failures=3, reset_timeout=60)

    def execute_pipeline(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the full EJE critic/aggregation/audit pipeline with error handling and recovery.
        Args:
            case_data: Dictionary of fact pattern and contextual inputs.
        Returns:
            Dict containing aggregated decision, critics responses, audit record.
        """
        critics = self.critic_loader.load_critics()  # Load all critic modules
        critic_results = []
        for critic in critics:
            try:
                result = self.circuit_breaker.call(
                    lambda: critic.analyze(case_data)
                )
                critic_results.append(result)
            except RetryableError as e:
                recovery = error_recovery(e, context={'critic': critic.name})
                critic_results.append({'error': str(e), 'recovery': recovery})
            except Exception as ex:
                self.audit_logger.log_error('Critic Failure', str(ex), critic.name)
                critic_results.append({'error': str(ex)})

        aggregated = self.aggregator.aggregate(critic_results)
        audit_record = self.audit_logger.log_decision(case_data, aggregated, critic_results)
        engine_result = self.reasoning_engine.run_decision(aggregated)
        return {
            'engine_decision': engine_result,
            'critic_results': critic_results,
            'aggregated': aggregated,
            'audit': audit_record
        }

    def fetch_precedents(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Searches precedents using aggregator.
        Args:
            query: Search parameters.
        Returns:
            List of precedent records.
        """
        return self.aggregator.search_precedents(query)

    def log_custom_event(self, event_type: str, detail: str):
        """
        Log arbitrary event to audit log.
        Args:
            event_type: Type of event.
          feat: Integration layer bridging infrastructure and core EJE engine

- Integrates API/SDK and testing modules with core engine (aggregator, audit_log, critic_loader, ethical_reasoning_engine)
- Implements robust error handling and circuit breaker around critic and engine pipeline
- Wires audit logging and decision capture throughout
- Provides unified interface for full EJE pipeline execution
- Supports precedent search for case law recall
- Fulfills Q1-Q4 roadmap integration requirements for production delivery

Copyright Eleanor Project, 2026. See code file for full docstring and method details.
  detail: Detail string.
        """
        self.audit_logger.log_event(event_type, detail)

# Example usage for API endpoint integration:
# integration = EJEIntegration(config)
# response = integration.execute_pipeline(case_data)
