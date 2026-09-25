"""
Data Preprocessing Module
--------------------------
Loads the raw NCR ride-sharing dataset, cleans it, and writes a
processed CSV to data/processed/.
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def find_raw_csv() -> Path:
    """Auto-detects the dataset CSV in data/raw/ (ignores README.md)."""
    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV found in {RAW_DIR}. Download the dataset and place it there."
        )
    if len(csv_files) > 1:
        print(f"Multiple CSVs found, using the first: {csv_files[0].name}")
    return csv_files[0]


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns from {path.name}")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- Drop exact duplicate rows ---
    before = len(df)
    df = df.drop_duplicates()
    print(f"Dropped {before - len(df)} duplicate rows")

    # --- Combine Date + Time into a single datetime column ---
    if "Date" in df.columns and "Time" in df.columns:
        df["datetime"] = pd.to_datetime(
            df["Date"].astype(str) + " " + df["Time"].astype(str),
            errors="coerce",
        )
        n_bad = df["datetime"].isna().sum()
        if n_bad:
            print(f"Warning: {n_bad} rows had unparseable Date/Time, dropping them")
            df = df.dropna(subset=["datetime"])

        df["hour"] = df["datetime"].dt.hour
        df["day_of_week"] = df["datetime"].dt.day_name()
        df["date_only"] = df["datetime"].dt.date

    # --- Standardize categorical text columns (strip whitespace, consistent case) ---
    categorical_cols = [
        "Booking Status", "Vehicle Type", "Pickup Location", "Drop Location",
        "Payment Method", "Reason for cancelling by Customer",
        "Driver Cancellation Reason", "Incomplete Rides Reason",
    ]
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df.loc[df[col].isin(["nan", "None", ""]), col] = np.nan

    # --- Numeric columns: coerce to numeric, invalid entries become NaN ---
    numeric_cols = [
        "Avg VTAT", "Avg CTAT", "Booking Value", "Ride Distance",
        "Driver Ratings", "Customer Rating",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- Ride status flag, useful downstream for simulation calibration ---
    if "Booking Status" in df.columns:
        df["is_completed"] = df["Booking Status"].str.lower() == "completed"
        df["is_cancelled"] = df["Booking Status"].str.contains(
            "cancel", case=False, na=False
        )

    # --- Missing value report (no silent dropping of rows beyond duplicates/bad dates) ---
    missing = df.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        print("\nRemaining missing values per column:")
        print(missing.to_string())
        print(
            "\nNote: cancellation-reason and rating columns are expected to have "
            "missing values (e.g. a completed ride has no cancellation reason)."
        )

    return df


def save_data(df: pd.DataFrame, filename: str = "ncr_rides_cleaned.csv") -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / filename
    df.to_csv(out_path, index=False)
    print(f"\nSaved cleaned dataset: {out_path} ({len(df)} rows)")
    return out_path


def main():
    raw_path = find_raw_csv()
    df = load_data(raw_path)
    df_clean = clean_data(df)
    save_data(df_clean)


if __name__ == "__main__":
    main()