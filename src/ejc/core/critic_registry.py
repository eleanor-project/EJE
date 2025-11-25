class CriticRegistry:
    """
    Registry of all official critics included with EJE.
    Useful for inspector dashboards, metadata, and plugin validation.
    """

    def __init__(self):
        self._critics = {}

    def register(self, name, cls):
        self._critics[name] = cls

    def get(self, name):
        return self._critics.get(name)

    def list(self):
        return list(self._critics.keys())
