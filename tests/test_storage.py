from data.storage.sqlite_store import init_db


def test_init_db_runs():
    init_db()
    assert True
