from __future__ import annotations

import argparse
import sys
from pathlib import Path

from exolens.exporters import write_csv, write_json
from exolens.models.result import AnalysisStatus
from exolens.pipeline import AnalysisConfig, analyze_local_file, analyze_tess_target


def _add_search_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--period-min-days", type=float, default=0.5, help="Minimum searched period in days (default: 0.5).")
    parser.add_argument("--period-max-days", type=float, default=20.0, help="Maximum searched period in days (default: 20).")
    parser.add_argument("--duration-min-hours", type=float, default=0.5, help="Minimum searched transit duration in hours (default: 0.5).")
    parser.add_argument("--duration-max-hours", type=float, default=6.0, help="Maximum searched transit duration in hours (default: 6).")
    parser.add_argument("--n-periods", type=int, default=5000, help="Number of trial periods (default: 5000).")
    parser.add_argument("--n-durations", type=int, default=10, help="Number of trial durations (default: 10).")
    parser.add_argument("--min-points", type=int, default=20, help="Minimum valid observations required (default: 20).")
    parser.add_argument("--output", type=Path, help="JSON output path (default: data/results/<analysis-id>.json).")
    parser.add_argument("--csv", nargs="?", const="auto", help="Also write a flattened CSV summary; optionally provide its path.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="exolens", description="Analyze a TESS light curve using BLS.")
    commands = parser.add_subparsers(dest="command", required=True)

    local = commands.add_parser("analyze-file", help="Analyze a local CSV or FITS light curve.")
    local.add_argument("file", type=Path, help="CSV (time, flux; optional flux_err, quality) or FITS light curve.")
    local.add_argument("--tic-id", help="TIC ID only if known from the source.")
    local.add_argument("--sector", type=int, help="TESS sector only if known from source metadata.")
    local.add_argument("--mission", help="Mission name only if known.")
    local.add_argument("--author", help="Product author only if known.")
    local.add_argument("--cadence-seconds", type=float, help="Cadence only if known.")
    local.add_argument("--time-system", help="Explicit time system, e.g. 'BTJD (BJD - 2457000)'.")
    local.add_argument("--synthetic-test-data", action="store_true", help="Explicitly mark this local file as synthetic test data.")
    _add_search_options(local)

    tess = commands.add_parser("analyze-tic", help="Retrieve and analyze one selected TESS archive product.")
    tess.add_argument("tic_id", help="TIC number, with or without the 'TIC' prefix.")
    tess.add_argument("--sector", type=int, help="TESS sector to select; recommended when target has multiple sectors.")
    tess.add_argument("--author", help="Archive product author, e.g. TESS-SPOC; required to disambiguate authors.")
    tess.add_argument("--product-id", help="Exact archive observation/product ID to select.")
    tess.add_argument("--cache-dir", type=Path, default=Path("data/cache"), help="Download cache directory (default: data/cache).")
    _add_search_options(tess)
    return parser


def _config(args: argparse.Namespace) -> AnalysisConfig:
    return AnalysisConfig(
        period_min_days=args.period_min_days,
        period_max_days=args.period_max_days,
        duration_min_hours=args.duration_min_hours,
        duration_max_hours=args.duration_max_hours,
        n_periods=args.n_periods,
        n_durations=args.n_durations,
        min_points=args.min_points,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = _config(args)
    except ValueError as exc:
        parser.error(str(exc))

    if args.command == "analyze-file":
        result = analyze_local_file(
            args.file,
            config=config,
            tic_id=args.tic_id,
            sector=args.sector,
            mission=args.mission,
            author=args.author,
            cadence_seconds=args.cadence_seconds,
            time_system=args.time_system,
            synthetic_test_data=args.synthetic_test_data,
        )
    else:
        result = analyze_tess_target(
            args.tic_id,
            config=config,
            sector=args.sector,
            author=args.author,
            product_id=args.product_id,
            cache_dir=args.cache_dir,
        )

    output_path = args.output or Path("data/results") / f"{result.analysis_id}.json"
    write_json(result, output_path)
    print(f"Analysis status: {result.analysis_status.value}")
    print(f"JSON result: {output_path}")
    if result.errors:
        for error in result.errors:
            print(f"{error.code}: {error.message}", file=sys.stderr)
    if args.csv is not None:
        csv_path = Path(args.csv) if args.csv != "auto" else output_path.with_suffix(".csv")
        write_csv(result, csv_path)
        print(f"CSV summary: {csv_path}")
    return 0 if result.analysis_status is not AnalysisStatus.FAILED else 2
