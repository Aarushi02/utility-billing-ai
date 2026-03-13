"""Import log files into the logs table."""

from src.database.db_utils import import_log_file


def main() -> None:
    # Adjust paths as needed.
    files = [
        ("logs/api.local.log", "api"),
        ("logs/streamlit.local.log", "streamlit"),
        ("logs/utility_billing.log", "utility_billing"),
    ]

    total = 0
    for path, source in files:
        inserted = import_log_file(path, source)
        print(f"{source}: inserted {inserted} rows from {path}")
        total += inserted

    print(f"Total inserted: {total}")


if __name__ == "__main__":
    main()
