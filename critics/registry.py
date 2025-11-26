# critics/registry.py

import importlib
from typing import Any, Dict, List

from core.errors import GovernanceError
from utils.logging import logger


REQUIRED_CRITIC_METHODS = ["evaluate", "name"]


class CriticRegistryError(GovernanceError):
    """Raised when critic loading fails."""
    pass


def validate_critic_interface(critic: Any, name: str):
    """
    Ensure each critic implements the required interface.
    """
    for method in REQUIRED_CRITIC_METHODS:
        if not hasattr(critic, method):
            raise CriticRegistryError(
                f"Critic '{name}' missing required method '{method}'."
            )


def load_class(module_path: str, class_name: str):
    """
    Dynamically import critic classes.
    """
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except Exception as e:
        raise CriticRegistryError(
            f"Failed to import {class_name} from {module_path}: {e}"
        )


def load_critics_from_config(config: List[Dict[str, Any]]):
    """
    Loads critics from the critics.yaml config file.

    Returns:
        List of instantiated critic classes, ordered by priority.
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
