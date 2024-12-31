from main import minus_months
from datetime import datetime



def test_minus_month():
    prev = minus_months(1, now=datetime(2024, 12, 31, 15, 0))
    assert prev == datetime(2024, 11, 30, 23, 59, 59, 999999)

    assert minus_months(2, now=datetime(2024, 4, 30, 15, 0)) == datetime(2024, 2, 29, 23, 59, 59, 999999)
    assert minus_months(2, now=datetime(2024, 2, 29, 9, 0)) == datetime(2023, 12, 29, 9, 0)
    assert minus_months(1, now=datetime(2024, 1, 1, 0, 0)) == datetime(2023, 12, 1, 0, 0)
