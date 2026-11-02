import argparse
from .pipeline import run_pipeline
from .config import PipelineConfig

def main():
    parser = argparse.ArgumentParser(description="Pipeline de pronóstico y abastecimiento Tostao.")
    parser.add_argument("--data-dir", required=True, help="Carpeta con los CSV de entrada.")
    parser.add_argument("--output-dir", default="outputs", help="Carpeta de salida.")
    parser.add_argument("--horizon-days", type=int, default=7)
    parser.add_argument("--safety-days", type=int, default=1)
    parser.add_argument("--service-level", type=float, default=0.90)
    args = parser.parse_args()

    config = PipelineConfig(
        horizon_days=args.horizon_days,
        safety_days=args.safety_days,
        default_service_level=args.service_level
    )
    summary, _ = run_pipeline(args.data_dir, args.output_dir, config)
    for key, value in summary.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()
