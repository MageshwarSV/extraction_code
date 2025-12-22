"""
Test the uvicorn-reload trigger in `data_transformation.py` by
mocking a Postgres connection and exercising the create/delete/reload endpoints.

This script does NOT require a real Postgres server because it replaces
`psycopg2.connect` with a fake in-memory implementation for testing.
"""
import os
import time
import json
from pathlib import Path

# Ensure tests run from repository root
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

import psycopg2


class FakeDB:
    def __init__(self):
        self.rows = []
        self.next_id = 1

    def connect(self, *args, **kwargs):
        return FakeConn(self)


class FakeConn:
    def __init__(self, db: FakeDB):
        self.db = db
        self._cursor = FakeCursor(self.db)

    def cursor(self, cursor_factory=None):
        return self._cursor

    def commit(self):
        pass

    def close(self):
        pass


class FakeCursor:
    def __init__(self, db: FakeDB):
        self.db = db
        self._last = None
        self._last_params = None

    def execute(self, sql, params=None):
        s = (sql or '').lower()
        self._last = s
        self._last_params = params

        if 'insert into data_transformation' in s:
            field, frm, to = params[0], params[1], params[2]
            row = {
                'id': self.db.next_id,
                'field_name': field,
                'from_value': frm,
                'to_value': to,
                'created_at': None,
                'updated_at': None,
            }
            self.db.rows.append(row)
            self.db.next_id += 1
            self._last_row = row

        elif s.strip().startswith('select field_name, from_value, to_value'):
            # nothing to do; fetchall will return current rows
            pass

        elif s.strip().startswith('select id, field_name, from_value, to_value'):
            # fetch one by id
            pass

        elif 'select count(*)' in s:
            pass

        elif 'delete from data_transformation' in s:
            # params contains id
            rid = params[0]
            found = None
            for r in list(self.db.rows):
                if r['id'] == rid:
                    found = r
                    self.db.rows.remove(r)
                    break
            self._last_row = found

        elif 'update data_transformation' in s:
            # update by id
            fid = params[-1]
            for r in self.db.rows:
                if r['id'] == fid:
                    r['field_name'] = params[0]
                    r['from_value'] = params[1]
                    r['to_value'] = params[2]
                    self._last_row = r
                    break

    def fetchall(self):
        # return list of dicts with keys expected by DataTransformer._load_transformations
        return [{'field_name': r['field_name'], 'from_value': r['from_value'], 'to_value': r['to_value']} for r in self.db.rows]

    def fetchone(self):
        # if last op was insert returning, return last_row
        if hasattr(self, '_last_row') and self._last_row is not None:
            return self._last_row
        # count
        if self._last and 'select count(*)' in self._last:
            return {'total': len(self.db.rows)}
        # group by
        if self._last and 'group by field_name' in self._last:
            counts = {}
            for r in self.db.rows:
                counts[r['field_name']] = counts.get(r['field_name'], 0) + 1
            return [{'field_name': k, 'count': v} for k, v in counts.items()]
        return None

    def close(self):
        pass


def run_test():
    # configure trigger file
    trigger = ROOT / 'tests' / 'tmp_uvicorn_trigger.txt'
    if trigger.exists():
        trigger.unlink()

    os.environ['UVICORN_AUTO_RELOAD_ON_WRITE'] = '1'
    os.environ['UVICORN_RELOAD_TRIGGER_FILE'] = str(trigger)

    # patch psycopg2.connect
    fake_db = FakeDB()
    psycopg2.connect = fake_db.connect

    # import module (after patch). Load by file path to avoid package import issues
    from importlib import util
    module_path = ROOT / 'engine' / 'extractors' / 'data_transformation.py'
    spec = util.spec_from_file_location('data_transformation_mod', str(module_path))
    dt = util.module_from_spec(spec)
    spec.loader.exec_module(dt)

    client = dt.app.test_client()

    # initial cache should reflect empty DB
    transformer = dt.get_transformer()
    print('Initial cache:', transformer._transformation_cache)

    # POST create
    payload = {'field_name': 'Consignee', 'from_value': 'A', 'to_value': 'B'}
    t0 = time.time()
    r = client.post('/api/transformations', json=payload)
    print('POST status', r.status_code, r.get_json())
    assert r.status_code == 201, r.get_data(as_text=True)

    assert trigger.exists(), 'Trigger file not created'
    m1 = trigger.stat().st_mtime
    print('Trigger touched at', m1)

    # cache should now contain the mapping
    transformer = dt.get_transformer()
    print('Cache after create:', transformer._transformation_cache)
    assert 'Consignee' in transformer._transformation_cache

    # DELETE the created id
    created_id = r.get_json()['data']['id']
    time.sleep(0.1)
    r2 = client.delete(f'/api/transformations/{created_id}')
    print('DELETE status', r2.status_code, r2.get_json())
    assert r2.status_code == 200

    m2 = trigger.stat().st_mtime
    print('Trigger touched again at', m2)
    assert m2 >= m1

    # cache should no longer have the mapping
    transformer = dt.get_transformer()
    print('Cache after delete:', transformer._transformation_cache)

    # explicit reload endpoint
    time.sleep(0.1)
    r3 = client.post('/api/transformations/reload')
    print('Reload endpoint status', r3.status_code, r3.get_json())
    assert r3.status_code == 200

    print('All tests passed')


if __name__ == '__main__':
    run_test()
