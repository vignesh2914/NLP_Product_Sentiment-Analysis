from datetime import datetime, timezone
import sys


def get_current_utc_datetime():
    try:
        current_utc_datetime = datetime.now(timezone.utc)
        print("current date time collected successfully")
        return current_utc_datetime
    except Exception as e:
        print(f"An error occurred: {e}")


def extract_utc_date_and_time(utc_datetime):
    try:
        utc_date = utc_datetime.strftime('%Y-%m-%d')
        utc_time = utc_datetime.strftime('%H:%M:%S')
        print("UTC date and UTC time colleceted")
        return utc_date, utc_time
    except Exception as e:
        print(f"An error occurred: {e}")


