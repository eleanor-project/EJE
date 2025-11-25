"""
Abstract base classes for EJE critics.
Provides strong interface contracts for critic implementations.
"""
import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol


class CriticSupplierProtocol(Protocol):
    """Protocol defining the interface for critic suppliers (LLM backends, rule engines, etc.)"""

    def run(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Execute the critic evaluation.

        Args:
            prompt: The evaluation prompt/case text
            **kwargs: Additional arguments for the supplier

        Returns:
            Dict with keys: verdict, confidence, justification
        """
        ...


class BaseCritic(ABC):
    """
    Abstract base class for all EJE critics.
    Enforces consistent interface and behavior across critic implementations.
    """

    def __init__(
        self,
        name: str,
        weight: float = 1.0,
        priority: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> None:
        """
        Initialize base critic.

        Args:
            name: Unique identifier for this critic
            weight: Aggregation weight (default: 1.0)
            priority: Priority level (None, 'override', 'high', etc.)
            timeout: Maximum execution time in seconds (None = no limit)
        """
        self.name: str = name
        self.weight: float = weight
        self.priority: Optional[str] = priority
        self.timeout: Optional[float] = timeout
        self._validate_init_params()

    def _validate_init_params(self) -> None:
        """Validate initialization parameters."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError(f"Critic name must be a non-empty string, got: {self.name}")
        if not isinstance(self.weight, (int, float)) or self.weight <= 0:
            raise ValueError(f"Weight must be positive number, got: {self.weight}")
        if self.priority is not None and not isinstance(self.priority, str):
            raise ValueError(f"Priority must be string or None, got: {self.priority}")
        if self.timeout is not None and (not isinstance(self.timeout, (int, float)) or self.timeout <= 0):
            raise ValueError(f"Timeout must be positive number or None, got: {self.timeout}")

    @abstractmethod
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a case and return verdict.

        Args:
            case: Dictionary containing at minimum:
                - text: str (required) - the case text to evaluate
                - context: dict (optional) - additional context
                - metadata: dict (optional) - metadata about the case

        Returns:
            Dictionary containing:
                - verdict: str (required) - one of: ALLOW, DENY, REVIEW, BLOCK
                - confidence: float (required) - value between 0.0 and 1.0
                - justification: str (required) - explanation of the verdict

        Raises:
            ValueError: If case format is invalid
            TimeoutError: If evaluation exceeds timeout
            Exception: For other evaluation errors
        """
        pass

    def _enrich_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Add critic metadata to output."""
        output['critic'] = self.name
        output['weight'] = self.weight
        output['priority'] = self.priority
        output['timestamp'] = datetime.datetime.utcnow().isoformat()
        return output

    def validate_case(self, case: Dict[str, Any]) -> None:
        """
        Validate case structure before evaluation.

        Args:
            case: The case dictionary to validate

        Raises:
            ValueError: If case is invalid
        """
        if not isinstance(case, dict):
            raise ValueError(f"Case must be a dictionary, got {type(case)}")
        if 'text' not in case:
            raise ValueError("Case must contain 'text' field")
        if not isinstance(case['text'], str):
            raise ValueError("Case 'text' field must be a string")

    def validate_output(self, output: Dict[str, Any]) -> None:
        """
        Validate critic output structure.

        Args:
            output: The output dictionary to validate

        Raises:
            ValueError: If output is invalid
        """
        required_fields = ['verdict', 'confidence', 'justification']
        for field in required_fields:
            if field not in output:
                raise ValueError(f"Critic output missing required field: {field}")

        valid_verdicts = ['ALLOW', 'DENY', 'REVIEW', 'BLOCK', 'ERROR']
        if output['verdict'] not in valid_verdicts:
            raise ValueError(f"Invalid verdict: {output['verdict']}. Must be one of {valid_verdicts}")

        if not isinstance(output['confidence'], (int, float)):
            raise ValueError(f"Confidence must be a number, got {type(output['confidence'])}")

        if not (0.0 <= output['confidence'] <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {output['confidence']}")

        if not isinstance(output['justification'], str):
            raise ValueError(f"Justification must be a string, got {type(output['justification'])}")


class CriticBase(BaseCritic):
    """
    Legacy-compatible critic base class with supplier pattern.
    Wraps a supplier (LLM backend, rule engine, etc.) and adds metadata.
    """

    def __init__(
        self,
        name: str,
        supplier: CriticSupplierProtocol,
        weight: float = 1.0,
        priority: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> None:
        """
        Initialize critic with supplier.

        Args:
            name: Unique identifier for this critic
            supplier: Backend supplier implementing CriticSupplierProtocol
            weight: Aggregation weight
            priority: Priority level
            timeout: Maximum execution time in seconds
        """
        super().__init__(name=name, weight=weight, priority=priority, timeout=timeout)
        self.supplier: CriticSupplierProtocol = supplier

    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate case using supplier and enrich with metadata.

        Args:
            case: Case dictionary with 'text' field

        Returns:
            Enriched output with verdict, confidence, justification, and metadata
        """
        self.validate_case(case)

        # Extract prompt from case
        prompt = case.get('text', '')
        context = case.get('context')

        # Call supplier
        output = self.supplier.run(prompt, context=context)

        # Validate and enrich
        self.validate_output(output)
        return self._enrich_output(output)


class RuleBasedCritic(BaseCritic):
    """
    Abstract base class for rule-based critics.
    Subclasses implement apply_rules() method with custom logic.
    """

    @abstractmethod
    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply rule logic to case.

        Args:
            case: Case dictionary

        Returns:
            Dict with verdict, confidence, justification
        """
        pass

    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate case using rule logic.

        Args:
            case: Case dictionary

        Returns:
            Enriched output with verdict, confidence, justification
        """
        self.validate_case(case)
        output = self.apply_rules(case)
        self.validate_output(output)
        return self._enrich_output(output)
