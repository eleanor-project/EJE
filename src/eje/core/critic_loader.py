import importlib.util
import os

def load_all_plugins(plugin_paths):
    critics = []
    for py_file in plugin_paths:
        if not os.path.exists(py_file):
            continue
        spec = importlib.util.spec_from_file_location("plugcritic", py_file)
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
