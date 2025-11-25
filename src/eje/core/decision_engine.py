import uuid
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .critic_loader import load_all_plugins
from .aggregator import Aggregator
from .config_loader import load_global_config
from .precedent_manager import PrecedentManager
from .audit_log import AuditLogger
from .retraining_manager import Retrainer
from ..utils.logging import get_logger
from ..utils.validation import validate_case
from ..exceptions import CriticException, APIException
from ..constants import (
    MAX_RETRY_ATTEMPTS,
    RETRY_MIN_WAIT,
    RETRY_MAX_WAIT,
    RETRY_MULTIPLIER,
    DEFAULT_MAX_PARALLEL_CALLS,
    MIN_CONFIDENCE_FOR_RETRAINING,
    VERDICT_REVIEW
)


class DecisionEngine:
    """
    Core orchestrator of the Ethics Jurisprudence Engine (EJE).
    Executes multiple critics in parallel, aggregates their results,
    applies precedence + policy logic, and logs decisions.
    """

    def __init__(self, config_path="config/global.yaml"):
        self.logger = get_logger("EJE.DecisionEngine")

        self.logger.info("Loading global configuration...")
        self.config = load_global_config(config_path)

        self.logger.info("Loading critics...")
        self.critics = load_all_plugins(self.config.get("plugin_critics", []))

        self.pm = PrecedentManager(self.config.get("data_path", "./eleanor_data"))
        self.audit = AuditLogger(self.config.get("db_uri"))

        self.weights = self.config.get("critic_weights", {})
        self.priorities = self.config.get("critic_priorities", {})
        self.aggregator = Aggregator(self.config)

        # Initialize retraining manager
        self.retrainer = Retrainer(self.config, self.audit)

        # Get max parallel workers from config
        self.max_workers = self.config.get("max_parallel_calls", DEFAULT_MAX_PARALLEL_CALLS)

        self.logger.info(f"{len(self.critics)} critics loaded.")

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER,
            min=RETRY_MIN_WAIT,
            max=RETRY_MAX_WAIT
        ),
        retry=retry_if_exception_type((APIException, ConnectionError, TimeoutError)),
        reraise=True
    )
    def _evaluate_critic_with_retry(self, critic, case):
        """
        Evaluate a single critic with automatic retry logic.

        Args:
            critic: The critic instance to evaluate
            case: The case dictionary to evaluate

        Returns:
            dict: Critic output with verdict, confidence, and justification

        Raises:
            CriticException: If critic evaluation fails after all retries
        """
        try:
            return critic.evaluate(case)
        except (ConnectionError, TimeoutError) as e:
            self.logger.warning(f"Retryable error in {critic.__class__.__name__}: {str(e)}")
            raise APIException(f"API call failed: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Non-retryable error in {critic.__class__.__name__}: {str(e)}")
            raise CriticException(f"Critic evaluation failed: {str(e)}") from e

    def _evaluate_single_critic(self, critic, case):
        """
        Evaluate a single critic and format the output.

        Args:
            critic: The critic instance to evaluate
            case: The case dictionary to evaluate

        Returns:
            dict: Formatted critic output with metadata
        """
        critic_name = critic.__class__.__name__

        try:
            out = self._evaluate_critic_with_retry(critic, case)
            return {
                "critic": critic_name,
                "verdict": out["verdict"],
                "confidence": out["confidence"],
                "justification": out["justification"],
                "weight": self.weights.get(critic_name, 1.0),
                "priority": self.priorities.get(critic_name)
            }
        except (CriticException, APIException) as e:
            self.logger.error(f"Critic {critic_name} failed after retries: {str(e)}")
            return {
                "critic": critic_name,
                "verdict": "ERROR",
                "confidence": 0,
                "justification": f"Critic failed: {str(e)}",
                "weight": self.weights.get(critic_name, 1.0),
                "priority": self.priorities.get(critic_name)
            }
        except Exception as e:
            self.logger.error(f"Unexpected error in {critic_name}: {str(e)}")
            return {
                "critic": critic_name,
                "verdict": "ERROR",
                "confidence": 0,
                "justification": f"Unexpected error: {str(e)}",
                "weight": self.weights.get(critic_name, 1.0),
                "priority": self.priorities.get(critic_name)
            }

    def evaluate(self, case: dict) -> dict:
        """
        Evaluate a case using all configured critics in parallel.

        Args:
            case: Dictionary containing the case to evaluate

        Returns:
            dict: Complete decision bundle with results and metadata

        Raises:
            ValidationException: If case validation fails
        """
        validate_case(case)

        request_id = str(uuid.uuid4())
        timestamp = datetime.datetime.utcnow().isoformat()

        self.logger.info(f"Evaluating case {request_id}")

        # Execute critics in parallel using ThreadPoolExecutor
        critic_outputs = []

        if len(self.critics) == 0:
            self.logger.warning("No critics loaded, evaluation skipped")
        elif len(self.critics) == 1:
            # Single critic - no need for parallel execution
            critic_outputs.append(self._evaluate_single_critic(self.critics[0], case))
        else:
            # Multiple critics - execute in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all critic evaluation tasks
                future_to_critic = {
                    executor.submit(self._evaluate_single_critic, critic, case): critic
                    for critic in self.critics
                }

                # Collect results as they complete
                for future in as_completed(future_to_critic):
                    critic = future_to_critic[future]
                    try:
                        result = future.result()
                        critic_outputs.append(result)
                    except Exception as e:
                        # This should rarely happen as exceptions are handled in _evaluate_single_critic
                        critic_name = critic.__class__.__name__
                        self.logger.error(f"Future failed for {critic_name}: {str(e)}")
                        critic_outputs.append({
                            "critic": critic_name,
                            "verdict": "ERROR",
                            "confidence": 0,
                            "justification": f"Thread execution failed: {str(e)}",
                            "weight": self.weights.get(critic_name, 1.0),
                            "priority": self.priorities.get(critic_name)
                        })

        # Weighted aggregation
        final = self.aggregator.aggregate(critic_outputs)

        # Retrieve similar precedent
        precedent_refs = self.pm.lookup(case)

        # Bundle output
        bundle = {
            "request_id": request_id,
            "timestamp": timestamp,
            "input": case,
            "critic_outputs": critic_outputs,
            "final_decision": final,
            "precedent_refs": precedent_refs
        }

        # Store new precedent
        self.pm.store_precedent(bundle)

        # Audit logging
        self.audit.log_decision(bundle)

        # Feed to retraining manager if high confidence
        if final['overall_verdict'] != VERDICT_REVIEW:
            if final.get('avg_confidence', 0) >= MIN_CONFIDENCE_FOR_RETRAINING:
                self.retrainer.maybe_retrain(final, critic_outputs)

        self.logger.info(f"Case {request_id} evaluated: {final['overall_verdict']}")

        return bundle
