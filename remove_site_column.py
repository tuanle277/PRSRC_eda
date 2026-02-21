import pandas as pd
import os

DATA_PATH = "data"
OUTPUT_FOLDER = "removed_sites"

# Sites to remove
SITES_TO_REMOVE = [5, 6, 16, 17, 19, 29]


def main():
    data_dir = os.path.join(os.path.dirname(__file__), DATA_PATH)
    output_dir = os.path.join(data_dir, OUTPUT_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    processed = []
    skipped = []

    for filename in csv_files:
        filepath = os.path.join(data_dir, filename)
        try:
            df = pd.read_csv(
                filepath, on_bad_lines="skip", engine="python", encoding="utf-8"
            )
        except UnicodeDecodeError:
            df = pd.read_csv(
                filepath, on_bad_lines="skip", engine="python", encoding="latin-1"
            )
        except TypeError:
            try:
                df = pd.read_csv(
                    filepath, error_bad_lines=False, engine="python", encoding="utf-8"
                )
            except UnicodeDecodeError:
                df = pd.read_csv(
                    filepath, error_bad_lines=False, engine="python", encoding="latin-1"
                )

        # Case-insensitive check for "site" column
        site_col = None
        for c in df.columns:
            if c.strip().lower() == "site":
                site_col = c
                break

        if site_col is not None:
            # Coerce to numeric so "5" and 5 both match
            site_vals = pd.to_numeric(df[site_col], errors="coerce")
            mask = ~site_vals.isin(SITES_TO_REMOVE)
            df_out = df.loc[mask].copy()
            outpath = os.path.join(output_dir, filename)
            df_out.to_csv(outpath, index=False)
            processed.append(filename)
        else:
            skipped.append(filename)

    print(f"Created folder: {output_dir}")
    print(f"Filtered out sites {SITES_TO_REMOVE} from {len(processed)} file(s):")
    for f in processed:
        print(f"  - {f}")
    if skipped:
        print(f"Skipped {len(skipped)} file(s) (no 'site' column):")
        for f in skipped:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
