from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from exolens.errors import ExoLensError
from exolens.models.result import Provenance, SourceType, Target


@dataclass(frozen=True)
class LightCurveData:
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray | None
    quality: np.ndarray | None
    target: Target
    provenance: Provenance
    data_kind: str = "real_observation"


def _normalise_tic_id(value: str | None) -> str | None:
    if not value:
        return None
    digits = value.strip().upper().removeprefix("TIC").strip()
    if not digits.isdigit():
        raise ExoLensError("INVALID_TARGET", "TIC ID must contain a numeric identifier.")
    return f"TIC {digits}"


def _float_column(rows: list[dict[str, str]], key: str, *, required: bool) -> np.ndarray | None:
    values: list[float] = []
    for row_number, row in enumerate(rows, start=2):
        raw = row.get(key, "").strip()
        if not raw:
            if required:
                values.append(float("nan"))
            else:
                values.append(float("nan"))
            continue
        try:
            values.append(float(raw))
        except ValueError as exc:
            raise ExoLensError(
                "INVALID_LIGHT_CURVE", f"Column '{key}' has a non-numeric value on CSV row {row_number}."
            ) from exc
    return np.asarray(values, dtype=float)


def _parse_csv(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ExoLensError("INVALID_LIGHT_CURVE", "CSV file is empty or has no header row.")
            names = {name.strip().lower(): name for name in reader.fieldnames if name}
            if "time" not in names or "flux" not in names:
                raise ExoLensError("INVALID_LIGHT_CURVE", "CSV must contain 'time' and 'flux' columns.")
            rows = list(reader)
    except OSError as exc:
        raise ExoLensError("INVALID_LIGHT_CURVE", f"Could not read local light-curve file: {exc}") from exc

    time = _float_column(rows, names["time"], required=True)
    flux = _float_column(rows, names["flux"], required=True)
    flux_err = _float_column(rows, names["flux_err"], required=False) if "flux_err" in names else None
    quality = _float_column(rows, names["quality"], required=False) if "quality" in names else None
    assert time is not None and flux is not None
    return time, flux, flux_err, quality


def _read_fits(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None, dict[str, Any]]:
    try:
        import lightkurve as lk

        lc = lk.read(path)
    except Exception as exc:
        raise ExoLensError("INVALID_LIGHT_CURVE", f"Could not read FITS light curve: {exc}") from exc
    meta = dict(getattr(lc, "meta", {}) or {})
    time = np.asarray(lc.time.value, dtype=float)
    flux = np.asarray(np.ma.filled(lc.flux.value, np.nan), dtype=float)
    flux_err = None
    if getattr(lc, "flux_err", None) is not None:
        flux_err = np.asarray(np.ma.filled(lc.flux_err.value, np.nan), dtype=float)
    quality = getattr(lc, "quality", None)
    quality_array = np.asarray(quality, dtype=float) if quality is not None else None
    try:
        time_system = str(lc.time.format).upper()
        meta.setdefault("TIMESYS", "BTJD" if time_system == "BTJD" else time_system)
    except Exception:
        pass
    return time, flux, flux_err, quality_array, meta


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _meta_value(meta: dict[str, Any], *names: str) -> Any:
    lookup = {str(key).upper(): value for key, value in meta.items()}
    for name in names:
        value = lookup.get(name.upper())
        if value is not None and str(value).strip():
            return value
    return None


def load_local_file(
    filename: str | Path,
    *,
    tic_id: str | None = None,
    sector: int | None = None,
    mission: str | None = None,
    author: str | None = None,
    cadence_seconds: float | None = None,
    time_system: str | None = None,
    synthetic_test_data: bool = False,
) -> LightCurveData:
    path = Path(filename).expanduser()
    if not path.is_file():
        raise ExoLensError("NO_LIGHT_CURVE", f"Local light-curve file does not exist: {path.name}")

    suffixes = "".join(path.suffixes).lower()
    meta: dict[str, Any] = {}
    if suffixes.endswith(".csv"):
        time, flux, flux_err, quality = _parse_csv(path)
    elif suffixes.endswith((".fits", ".fit", ".fits.gz", ".fit.gz")):
        time, flux, flux_err, quality, meta = _read_fits(path)
    else:
        raise ExoLensError("INVALID_LIGHT_CURVE", "Supported local formats are CSV and FITS (.fits/.fit, optionally gzipped).")

    resolved_tic = _normalise_tic_id(tic_id or _meta_value(meta, "TICID", "TIC_ID", "OBJECT"))
    resolved_sector = sector
    if resolved_sector is None:
        raw_sector = _meta_value(meta, "SECTOR", "SECTOR_NUMBER")
        try:
            resolved_sector = int(raw_sector) if raw_sector is not None else None
        except (TypeError, ValueError):
            resolved_sector = None
    resolved_mission = mission or _meta_value(meta, "TELESCOP", "MISSION")
    resolved_author = author or _meta_value(meta, "AUTHOR", "ORIGIN")
    resolved_time_system = time_system or _meta_value(meta, "TIMESYS", "TIMEUNIT")
    if suffixes.endswith(".csv") and time_system is None and not resolved_time_system:
        resolved_time_system = None

    finite_times = time[np.isfinite(time)]
    prov = Provenance(
        mission=str(resolved_mission) if resolved_mission else None,
        sector=resolved_sector,
        data_author=str(resolved_author) if resolved_author else None,
        source_type=SourceType.SYNTHETIC_FIXTURE if synthetic_test_data else SourceType.LOCAL_FILE,
        source_filename=path.name,
        source_file_sha256=_sha256(path),
        cadence_seconds=cadence_seconds,
        time_system=str(resolved_time_system) if resolved_time_system else None,
        time_start=float(np.min(finite_times)) if finite_times.size else None,
        time_end=float(np.max(finite_times)) if finite_times.size else None,
    )
    return LightCurveData(
        time, flux, flux_err, quality, Target(tic_id=resolved_tic), prov,
        data_kind="synthetic_test" if synthetic_test_data else "real_observation",
    )


def _product_metadata(search_result: Any, index: int) -> dict[str, Any]:
    row = search_result.table[index]
    values: dict[str, Any] = {}
    for key in search_result.table.colnames:
        try:
            values[key.lower()] = row[key].item() if hasattr(row[key], "item") else row[key]
        except Exception:
            values[key.lower()] = row[key]
    return values


def _sector_from_product(meta: dict[str, Any]) -> int | None:
    for key in ("sequence_number", "sector"):
        value = meta.get(key)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
    mission_text = str(meta.get("mission", ""))
    match = re.search(r"sector\s+(\d+)", mission_text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def download_tess_target(
    tic_id: str,
    *,
    sector: int | None = None,
    author: str | None = None,
    product_id: str | None = None,
    cache_dir: str | Path = "data/cache",
) -> LightCurveData:
    resolved_tic = _normalise_tic_id(tic_id)
    assert resolved_tic is not None
    try:
        import lightkurve as lk
    except ImportError as exc:
        raise ExoLensError("DOWNLOAD_FAILED", "Lightkurve is not installed; install the project dependencies.") from exc

    try:
        search = lk.search_lightcurve(resolved_tic, mission="TESS", sector=sector, author=author)
    except Exception as exc:
        raise ExoLensError("DOWNLOAD_FAILED", f"MAST search failed: {exc}", retryable=True) from exc
    if len(search) == 0:
        raise ExoLensError("NO_LIGHT_CURVE", f"No TESS light curve found for {resolved_tic} with the selected options.")

    indexed_rows = [(i, _product_metadata(search, i)) for i in range(len(search))]
    rows = [row for _, row in indexed_rows]
    if product_id:
        rows = [row for row in rows if str(row.get("obs_id", row.get("obsid", ""))) == product_id]
        if not rows:
            raise ExoLensError("NO_LIGHT_CURVE", "No matching product_id was returned by the TESS archive search.")
    if sector is None:
        sectors = {s for row in rows if (s := _sector_from_product(row)) is not None}
        if len(sectors) > 1:
            raise ExoLensError("AMBIGUOUS_PRODUCT", "Multiple TESS sectors are available; select one with --sector.")
    if author is None:
        authors = {str(row.get("author")) for row in rows if row.get("author") is not None}
        if len(authors) > 1:
            raise ExoLensError("AMBIGUOUS_PRODUCT", "Multiple data authors are available; select one with --author.")
    if len(rows) > 1 and not product_id:
        ids = {str(row.get("obs_id", row.get("obsid", ""))) for row in rows}
        if len(ids) > 1:
            raise ExoLensError(
                "AMBIGUOUS_PRODUCT",
                "Multiple TESS products match. Narrow the selection with --sector, --author, or --product-id.",
            )

    selected_product_id = rows[0].get("obs_id", rows[0].get("obsid"))
    selected_index = next((i for i, row in indexed_rows if row.get("obs_id", row.get("obsid")) == selected_product_id), indexed_rows[0][0])
    product = rows[0]
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    try:
        lc = search[selected_index].download(download_dir=str(Path(cache_dir)))
    except Exception as exc:
        raise ExoLensError("DOWNLOAD_FAILED", f"Could not download the selected MAST light curve: {exc}", retryable=True) from exc
    if lc is None:
        raise ExoLensError("NO_LIGHT_CURVE", "The selected archive search result returned no light curve.")

    time = np.asarray(lc.time.value, dtype=float)
    flux = np.asarray(np.ma.filled(lc.flux.value, np.nan), dtype=float)
    flux_err = None
    if getattr(lc, "flux_err", None) is not None:
        flux_err = np.asarray(np.ma.filled(lc.flux_err.value, np.nan), dtype=float)
    quality_value = getattr(lc, "quality", None)
    quality = np.asarray(quality_value, dtype=float) if quality_value is not None else None
    meta = dict(getattr(lc, "meta", {}) or {})
    resolved_sector = sector or _sector_from_product(product) or _sector_from_product({k.lower(): v for k, v in meta.items()})
    resolved_author = author or product.get("author") or _meta_value(meta, "AUTHOR")
    time_format = str(getattr(lc.time, "format", "")).upper()
    resolved_time_system = "BTJD (BJD - 2457000)" if time_format == "BTJD" else (time_format or None)
    finite_times = time[np.isfinite(time)]
    provenance = Provenance(
        mission="TESS",
        sector=resolved_sector,
        data_author=str(resolved_author) if resolved_author else None,
        product_id=str(product.get("obs_id", product.get("obsid"))) if product.get("obs_id", product.get("obsid")) is not None else None,
        source_type=SourceType.MAST_PRODUCT,
        retrieved_at_utc=datetime.now(UTC),
        cadence_seconds=float(product["exptime"]) if product.get("exptime") is not None else None,
        time_system=resolved_time_system,
        time_start=float(np.min(finite_times)) if finite_times.size else None,
        time_end=float(np.max(finite_times)) if finite_times.size else None,
    )
    return LightCurveData(time, flux, flux_err, quality, Target(tic_id=resolved_tic), provenance)

