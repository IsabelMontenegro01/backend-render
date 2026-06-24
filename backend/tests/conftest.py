import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import app
from app.database.supabase_client import get_client


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __bool__(self):
        return bool(self.data)


class FakeTable:
    def __init__(self, store: dict, name: str):
        self.store = store
        self.name = name
        self.operation = None
        self.payload = None
        self.conditions = []
        self.order_field = None
        self.order_desc = False
        self.limit_count = None
        self.single = False
        self.negate_next = False
        self.on_conflict = None

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self.operation = "upsert"
        self.payload = payload
        self.on_conflict = on_conflict
        return self

    def select(self, *fields):
        self.operation = "select"
        self.fields = fields
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, field, value):
        self.conditions.append((field, "==", None if value == "null" else value))
        return self

    def order(self, field, desc=False):
        self.order_field = field
        self.order_desc = desc
        return self

    def limit(self, n):
        self.limit_count = n
        return self

    def maybe_single(self):
        self.single = True
        return self

    def not_(self):
        self.negate_next = True
        return self

    def is_(self, field, value):
        op = "!=" if self.negate_next else "=="
        self.negate_next = False
        self.conditions.append((field, op, None if value == "null" else value))
        return self

    def execute(self):
        table = self.store.setdefault(self.name, [])
        if self.operation == "insert":
            return FakeResponse(self._do_insert(table, self.payload))
        if self.operation == "upsert":
            return FakeResponse(self._do_upsert(table, self.payload, self.on_conflict))
        if self.operation == "select":
            return FakeResponse(self._do_select(table))
        if self.operation == "update":
            return FakeResponse(self._do_update(table, self.payload))
        return FakeResponse(None)

    def _do_insert(self, table, payload):
        if isinstance(payload, list):
            inserted = []
            for item in payload:
                row = self._make_row(table, item)
                table.append(row)
                inserted.append(row)
            return inserted
        row = self._make_row(table, payload)
        table.append(row)
        return [row]

    def _make_row(self, table, payload):
        row = payload.copy()
        row["id"] = len(table) + 1
        if "timestamp" not in row:
            row["timestamp"] = "2026-01-01T00:00:00Z"
        return row

    def _do_upsert(self, table, payload, on_conflict):
        if on_conflict == "route_id":
            for row in table:
                if row.get("route_id") == payload.get("route_id"):
                    row.update(payload)
                    return [row]
        row = self._make_row(table, payload)
        table.append(row)
        return [row]

    def _do_select(self, table):
        rows = [row.copy() for row in table]
        for field, op, value in self.conditions:
            if op == "==":
                rows = [row for row in rows if row.get(field) == value]
            else:
                rows = [row for row in rows if row.get(field) != value]
        if self.order_field:
            rows.sort(key=lambda row: row.get(self.order_field), reverse=self.order_desc)
        if self.limit_count is not None:
            rows = rows[: self.limit_count]
        if self.single:
            return rows[0] if rows else None
        return rows

    def _do_update(self, table, payload):
        updated = []
        for row in table:
            if all(self._matches(row, field, op, value) for field, op, value in self.conditions):
                row.update(payload)
                updated.append(row.copy())
        return updated

    def _matches(self, row, field, op, value):
        if op == "==":
            return row.get(field) == value
        return row.get(field) != value


class FakeSupabaseClient:
    def __init__(self):
        self.store = {}

    def table(self, name: str):
        return FakeTable(self.store, name)


@pytest.fixture(autouse=True)
def fake_supabase(monkeypatch):
    fake_client = FakeSupabaseClient()
    module_names = [
        "app.database.supabase_client",
        "app.routers.drones",
        "app.routers.voos",
        "app.routers.telemetria",
        "app.routers.deteccoes",
        "app.routers.consultas_pier",
        "app.routers.alertas",
        "app.routers.dashboard",
        "app.routers.rotas",
        "app.services.processamento_deteccao",
    ]
    for module_name in module_names:
        module = __import__(module_name, fromlist=["*"])
        if hasattr(module, "get_client"):
            monkeypatch.setattr(module, "get_client", lambda: fake_client)
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
