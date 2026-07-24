import os

os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: richiede service container reali (Postgres/Kafka), non gira nel job unit test",
    )
