from abc import ABC, abstractmethod


class BaseReranker(ABC):
    @abstractmethod
    def predict(self, sentences: list[tuple[str, str]]) -> list[float] | None:
        pass
