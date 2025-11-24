import uuid
import datetime
from .critic_loader import load_plugin_critics
from .aggregator import aggregate_scores
from .config_loader import load_global_config
from .precedent_manager import PrecedentManager
from .audit_log import AuditLogger
from ..utils.logging import get_logger
from ..utils.validation import validate_case


class DecisionEngine:
    """
    Core orchestrator of the Ethics Jurisprudence Engine (EJE).
    Executes multiple critics, aggregates their results,
    applies precedence + policy logic, and logs decisions.
    """

    def __init__(self, config_path="config/global.yaml"):
        self.logger = get_logger("EJE.DecisionEngine")

        self.logger.info("Loading global configuration...")
        self.config = load_global_config(config_path)

        self.logger.info("Loading critics...")
        self.critics = load_plugin_critics(self.config.get("plugin_critics", []))

        self.pm = PrecedentManager(self.config.get("data_path", "./eleanor_data"))
        self.audit = AuditLogger(self.config.get("db_uri"))

        self.weights = self.config.get("critic_weights", {})
        self.priorities = self.config.get("critic_priorities", {})

        self.logger.info(f"{len(self.critics)} critics loaded.")

    def evaluate(self, case: dict) -> dict:
        validate_case(case)

        request_id = str(uuid.uuid4())
        timestamp = datetime.datetime.utcnow().isoformat()

        self.logger.info(f"Evaluating case {request_id}")

        critic_outputs = []
        for critic in self.critics:
            try:
                out = critic.evaluate(case)
                critic_outputs.append({
                    "critic": critic.__class__.__name__,
                    "verdict": out["verdict"],
                    "confidence": out["confidence"],
                    "justification": out["justification"],
                })
            except Exception as e:
                critic_outputs.append({
                    "critic": critic.__class__.__name__,
                    "verdict": "ERROR",
                    "confidence": 0,
                    "justification": f"Critic failed: {str(e)}",
                })

        # Weighted aggregation
        final = aggregate_scores(
            critic_outputs,
            weights=self.weights,
            priorities=self.priorities
        )

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

        return bundle
