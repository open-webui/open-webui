from opentelemetry.metrics import Meter, Counter, Histogram, ObservableGauge
from pydantic import BaseModel, ValidationError


class MetricsDefinition(BaseModel):
    name: str
    type: str
    description: str
    unit: str


class MetricsService:
    def __init__(
        self,
        meter: Meter,
        definitions: list[dict] | list[MetricsDefinition] | None = None,
    ):
        self._meter = meter
        self._registry: dict[str, object] = {}

        if definitions:
            self._registry = self._create_registry_from_definitions(definitions)

    def _create_registry_from_definitions(self, definitions):
        registry = {}

        for raw_def in definitions:
            try:
                definition = (
                    raw_def
                    if isinstance(raw_def, MetricsDefinition)
                    else MetricsDefinition(**raw_def)
                )

                inst = self._create_instrument(definition)
                registry[definition.name] = inst

            except ValidationError as e:
                print(f"[MetricsService] Invalid metric definition {raw_def}: {e}")
            except Exception as e:
                print(f"[MetricsService] Failed to create '{raw_def}': {e}")

        return registry

    def _create_instrument(self, definition: MetricsDefinition):
        metric_type = definition.type.lower()

        try:
            if metric_type == "counter":
                return self._meter.create_counter(
                    name=definition.name,
                    description=definition.description,
                    unit=definition.unit,
                )

            elif metric_type == "histogram":
                return self._meter.create_histogram(
                    name=definition.name,
                    description=definition.description,
                    unit=definition.unit,
                )

            elif metric_type == "gauge":
                return self._meter.create_observable_gauge(
                    name=definition.name,
                    callbacks=[],
                    description=definition.description,
                    unit=definition.unit,
                )

            raise ValueError(f"Unknown metric type '{metric_type}'")

        except Exception as e:
            raise RuntimeError(f"Failed to create instrument '{definition.name}': {e}")

    def list_instruments(self):
        return list(self._registry.keys())

    def add_instrument(self, definition: MetricsDefinition):
        if definition.name in self._registry:
            raise KeyError(f"Instrument '{definition.name}' already exists")

        inst = self._create_instrument(definition)
        self._registry[definition.name] = inst
        return inst

    def counter(self, name: str) -> Counter:
        if name not in self._registry:
            definition = MetricsDefinition(
                name=name,
                type="counter",
                description=f"Counter for {name}",
                unit="",
            )
            self.add_instrument(definition)

        inst = self._registry[name]
        if not isinstance(inst, Counter):
            raise TypeError(f"'{name}' exists but is not a counter")

        return inst

    def histogram(self, name: str) -> Histogram:
        if name not in self._registry:
            definition = MetricsDefinition(
                name=name,
                type="histogram",
                description=f"Histogram for {name}",
                unit="",
            )
            self.add_instrument(definition)

        inst = self._registry[name]
        if not isinstance(inst, Histogram):
            raise TypeError(f"'{name}' exists but is not a histogram")

        return inst

    def gauge(self, name: str) -> ObservableGauge:
        if name not in self._registry:
            definition = MetricsDefinition(
                name=name,
                type="gauge",
                description=f"Gauge for {name}",
                unit="",
            )
            self.add_instrument(definition)

        inst = self._registry[name]
        if not isinstance(inst, ObservableGauge):
            raise TypeError(f"'{name}' exists but is not a gauge")

        return inst

    def create_counter(
        self, name: str, description: str = "", unit: str = ""
    ) -> Counter:
        definition = MetricsDefinition(
            name=name,
            type="counter",
            description=description,
            unit=unit,
        )
        return self.add_instrument(definition)

    def create_histogram(
        self, name: str, description: str = "", unit: str = ""
    ) -> Histogram:
        definition = MetricsDefinition(
            name=name,
            type="histogram",
            description=description,
            unit=unit,
        )
        return self.add_instrument(definition)

    def create_gauge(
        self, name: str, description: str = "", unit: str = ""
    ) -> ObservableGauge:
        definition = MetricsDefinition(
            name=name,
            type="gauge",
            description=description,
            unit=unit,
        )
        return self.add_instrument(definition)
