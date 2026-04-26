import pytest
from django.db import connection

@pytest.mark.django_db
def test_db_alive():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
        assert row[0] == 1
        print("DB IS ALIVE AND RESPONDING")
