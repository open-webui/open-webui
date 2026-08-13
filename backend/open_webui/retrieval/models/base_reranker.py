from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class BaseReranker(ABC):
    @abstractmethod
    def predict(self, sentences: List[Tuple[str, str]]) -> Optional[List[float]]:
        pass
