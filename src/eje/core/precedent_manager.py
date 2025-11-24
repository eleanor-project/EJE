import os
import json
import hashlib
from ..utils.filepaths import ensure_dir
from ..utils.logging import get_logger


class PrecedentManager:
    """
    Stores and retrieves precedent bundles.
    Provides basic structural similarity via hashed input.
    """

    def __init__(self, data_path="./eleanor_data"):
        self.logger = get_logger("EJE.PrecedentManager")
        ensure_dir(data_path)

        self.store_path = os.path.join(data_path, "precedent_store.json")

        if not os.path.exists(self.store_path):
            with open(self.store_path, "w") as f:
                json.dump([], f)

    def _hash_case(self, case):
        return hashlib.sha256(
            json.dumps(case, sort_keys=True).encode()
        ).hexdigest()

    def lookup(self, case):
        """Return all precedents with the same hashed structure."""
        with open(self.store_path, "r") as f:
            database = json.load(f)
        target_hash = self._hash_case(case)
        return [p for p in database if p.get("case_hash") == target_hash]

    def store_precedent(self, bundle):
        with open(self.store_path, "r") as f:
            database = json.load(f)

        bundle["case_hash"] = self._hash_case(bundle["input"])
        database.append(bundle)

        with open(self.store_path, "w") as f:
            json.dump(database, f, indent=2)
