from pathlib import Path
from src.preprocessing.preprocess import run as run_preprocessing
from src.eda import eda
from src.analytics import metrics
from src.scenarios import what_if

PROCESSED_FILE = Path(__file__).resolve().parent / "data" / "processed" / "ncr_rides_cleaned.csv"


def main():
    if not PROCESSED_FILE.exists():
        print("Processed dataset not found — running preprocessing...")
        run_preprocessing()
    else:
        print(f"Using existing processed dataset: {PROCESSED_FILE}")

    print("\n" + "=" * 50)
    print("STEP 1/3: Exploratory data analysis")
    print("=" * 50)
    eda.run()

    print("\n" + "=" * 50)
    print("STEP 2/3: Simulation + KPI analytics")
    print("=" * 50)
    metrics.main()

    print("\n" + "=" * 50)
    print("STEP 3/3: Scenario (what-if) analysis")
    print("=" * 50)
    what_if.main()

    print("\nDone. See outputs/reports/ and outputs/figures/ for results.")


if __name__ == "__main__":
    main()