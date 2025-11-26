# src/ejc/core/critic_registry_loader.py

import importlib
from typing import Any, Dict, List

from .error_handling import GovernanceException
from ..utils.logging import get_logger

logger = get_logger("ejc.critic_registry")


REQUIRED_CRITIC_METHODS = ["evaluate", "name"]


class CriticRegistryError(GovernanceException):
    """Raised when critic loading fails."""
    pass


def validate_critic_interface(critic: Any, name: str) -> None:
    """
    Ensure each critic implements the required interface.

    Args:
        critic: Critic instance to validate
        name: Name of the critic

    Raises:
        CriticRegistryError: If critic is missing required methods
    """
    for method in REQUIRED_CRITIC_METHODS:
        if not hasattr(critic, method):
            raise CriticRegistryError(
                f"Critic '{name}' missing required method '{method}'."
            )


def load_class(module_path: str, class_name: str) -> Any:
    """
    Dynamically import critic classes.

    Args:
        module_path: Python module path (e.g., 'src.ejc.critics.openai_critic')
        class_name: Name of the class to import

    Returns:
        The imported class

    Raises:
        CriticRegistryError: If import fails
    """
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except Exception as e:
        raise CriticRegistryError(
            f"Failed to import {class_name} from {module_path}: {e}"
        )


def load_critics_from_config(config: List[Dict[str, Any]]) -> List[Any]:
    """
    Loads critics from the critics.yaml config file.

    Args:
        config: List of critic configuration dictionaries

    Returns:
        List of instantiated critic classes, ordered by priority

    Raises:
        CriticRegistryError: If critic loading fails
    """
    if not config:
        raise CriticRegistryError("Critic configuration is empty or missing.")

    critics = []

    for c in config:
        name = c.get("name")
        module = c.get("module")
        class_name = c.get("class")
        priority = c.get("priority", 99)

        if not name or not module or not class_name:
            raise CriticRegistryError(
                f"Malformed critic entry: {c}"
            )

        # Load class
        CriticClass = load_class(module, class_name)

        # Instantiate critic
        try:
            critic_instance = CriticClass()
        except Exception as e:
            raise CriticRegistryError(
                f"Failed to instantiate critic '{name}': {e}"
            )

        # Validate interface
        validate_critic_interface(critic_instance, name)

        # Store critic + priority
        critics.append((priority, critic_instance))

        logger.info(f"Loaded critic: {name} (priority {priority})")

    # Sort: lowest priority number == highest importance
    critics.sort(key=lambda x: x[0])

    # Return critic instances in order
    ordered_critics = [c[1] for c in critics]

    logger.info(f"Critic load order: {[c.name for c in ordered_critics]}")
    return ordered_critics
