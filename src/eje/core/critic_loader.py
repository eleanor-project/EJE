import importlib.util
import os

def load_all_plugins(plugin_paths):
    critics = []
    for py_file in plugin_paths:
        if not os.path.exists(py_file): continue
        spec = importlib.util.spec_from_file_location("plugcritic", py_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        supplier = getattr(mod, "CustomCriticSupplier")()
        critics.append(supplier)
    return critics
