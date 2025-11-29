import importlib.util
import os
from typing import Iterable, List


class PluginSecurityError(Exception):
    """Raised when a plugin violates security constraints."""


def _is_in_allowed_root(path: str, allowed_root: str) -> bool:
    abs_path = os.path.abspath(path)
    abs_root = os.path.abspath(allowed_root)
    try:
        common = os.path.commonpath([abs_path, abs_root])
    except ValueError:
        return False
    return common == abs_root


def load_all_plugins(plugin_paths: Iterable[str], allowed_root: str = "./plugins") -> List[object]:
    """
    Load critic plugins from disk with minimal security validation.

    - Only python files under ``allowed_root`` are loaded.
    - Duplicate paths are ignored.
    - Missing files are skipped rather than crashing startup.
    """

    critics = []
    seen_paths = set()
    for py_file in plugin_paths:
        abs_path = os.path.abspath(py_file)
        if abs_path in seen_paths:
            continue
        seen_paths.add(abs_path)

        if not abs_path.endswith(".py"):
            raise PluginSecurityError(f"Plugin must be a .py file: {py_file}")

        if not _is_in_allowed_root(abs_path, allowed_root):
            raise PluginSecurityError(
                f"Plugin outside approved directory: {py_file} (allowed root: {allowed_root})"
            )

        if not os.path.exists(abs_path):
            continue

        spec = importlib.util.spec_from_file_location("plugcritic", abs_path)
        if not spec or not spec.loader:
            raise ImportError(f"Unable to load plugin spec for {py_file}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Try multiple possible class names for backward compatibility
        critic_class = None
        for class_name in ["CustomRuleCritic", "CustomCriticSupplier", "Critic"]:
            critic_class = getattr(mod, class_name, None)
            if critic_class:
                break

        if not critic_class:
            raise ValueError(f"No valid critic class found in {py_file}")

        critic = critic_class()
        critics.append(critic)
    return critics
