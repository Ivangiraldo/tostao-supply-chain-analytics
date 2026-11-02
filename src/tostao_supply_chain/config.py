from dataclasses import dataclass

@dataclass(frozen=True)
class PipelineConfig:
    horizon_days: int = 7
    safety_days: int = 1
    service_levels: tuple = (0.85, 0.90, 0.95)
    default_service_level: float = 0.90
    n_simulations: int = 10_000
    min_product_errors: int = 30
    random_seed: int = 42
    model_name: str = "ETS_Aditivo_7"

    @property
    def max_coverage_days(self) -> int:
        return self.horizon_days + self.safety_days
