import copy
from typing import Any


class StepTracerUtils:
    def safe_deepcopy(self, x: Any) -> Any:
        try:
            return copy.deepcopy(x)
        except Exception:
            return x
