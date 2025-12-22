"""Simple watcher script to observe transformation cache reloads.

Run this in a separate terminal while the API is running. It will print
the current mapping count and marker file mtime and report changes when
they occur (either via DB NOTIFY or the update marker touch).
"""
import time
import sys
from pprint import pprint
from pathlib import Path

# Ensure repo root is on sys.path so 'engine' package can be imported when running
# this script from the project root or tools directory.
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

try:
    from engine.extractors.data_transformation import get_transformer, _gather_marker_and_trigger_status
except Exception as e:
    print("Failed to import transformer module:", e)
    sys.exit(1)


def count_rules(transformer):
    try:
        return sum(len(v) for v in transformer._transformation_cache.values())
    except Exception:
        return 0


def main(poll_interval=1.0):
    transformer = get_transformer()
    last_count = count_rules(transformer)
    try:
        status = _gather_marker_and_trigger_status()
    except Exception:
        status = {}
    last_marker = status.get('marker_mtime')

    print("Watcher started. Initial rule count:", last_count)
    print("Initial marker status:")
    pprint(status)

    try:
        while True:
            time.sleep(poll_interval)
            try:
                status = _gather_marker_and_trigger_status()
                marker = status.get('marker_mtime')
                if marker != last_marker:
                    print(f"[watcher] Marker mtime changed: {last_marker} -> {marker}")
                    last_marker = marker

                cur = count_rules(transformer)
                if cur != last_count:
                    print(f"[watcher] Transformation count changed: {last_count} -> {cur}")
                    last_count = cur
            except Exception as ex:
                print("[watcher] error polling status:", ex)
    except KeyboardInterrupt:
        print("Watcher exiting")


if __name__ == '__main__':
    main()
