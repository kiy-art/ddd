import json
import queue

from app import progress

# conftest.py's autouse _fresh_progress_state fixture resets progress.py's
# module-level state (a deliberate single-process singleton - see its own
# docstring) before and after every test in the suite, this file included.


def _events_from(q: "queue.Queue[str]") -> list[dict]:
    events = []
    while True:
        try:
            line = q.get_nowait()
        except queue.Empty:
            break
        assert line.startswith("data: ") and line.endswith("\n\n")
        events.append(json.loads(line[len("data: ") : -2]))
    return events


def test_get_snapshot_sse_line_is_none_before_any_run():
    assert progress.get_snapshot_sse_line() is None


def test_subscribe_receives_the_full_run_lifecycle():
    sub_id, q = progress.subscribe()
    try:
        progress.start_run("fetch_rakuten", "日次バッチ処理")
        progress.start_stage("rakuten_prices")
        progress.update_stage_progress("rakuten_prices", 3, 10)
        progress.finish_stage("rakuten_prices", "更新3件 / スキップ0件")
        progress.finish_run()

        events = _events_from(q)
        assert [e["type"] for e in events] == [
            "run_started",
            "stage_started",
            "stage_progress",
            "stage_finished",
            "run_finished",
        ]
        assert events[0]["job"] == "fetch_rakuten"
        assert events[2]["stages"][0]["current"] == 3
        assert events[2]["stages"][0]["total"] == 10
        assert events[3]["stages"][0]["status"] == "done"
        assert events[3]["stages"][0]["detail"] == "更新3件 / スキップ0件"
        assert events[4]["status"] == "completed"
        assert events[4]["stage"] is None
    finally:
        progress.unsubscribe(sub_id)


def test_unsubscribe_stops_receiving_further_events():
    sub_id, q = progress.subscribe()
    progress.unsubscribe(sub_id)

    progress.start_run("run_update", "分析・AI説明文の再生成")
    progress.finish_run()

    assert _events_from(q) == []


def test_a_new_subscriber_can_bootstrap_from_the_current_snapshot():
    # subscribe() itself only opens an empty queue for future events (see
    # its docstring) - the /admin/live endpoint separately calls
    # get_snapshot_sse_line() once, right after subscribing, so a client
    # connecting mid-run isn't blank until the next event. This exercises
    # that same sequence.
    progress.start_run("fetch_rakuten", "日次バッチ処理")
    progress.start_stage("discovery")
    progress.update_stage_progress("discovery", 2, 5)

    sub_id, q = progress.subscribe()
    try:
        snapshot = progress.get_snapshot_sse_line()
        assert snapshot is not None
        event = json.loads(snapshot[len("data: ") : -2])
        assert event["type"] == "snapshot"
        assert event["job"] == "fetch_rakuten"
        assert event["stages"][0]["stage"] == "discovery"
        assert event["stages"][0]["current"] == 2
        # And the queue itself only has future events, not this bootstrap.
        assert _events_from(q) == []
    finally:
        progress.unsubscribe(sub_id)


def test_get_snapshot_sse_line_is_immune_to_later_mutation():
    # A regression test for a real bug caught during development: an
    # earlier version queued the mutable run dict itself, so a later
    # finish_stage() call could retroactively rewrite an SSE line already
    # sitting in a slow subscriber's queue by the time it was read. Lines
    # must be fully rendered (JSON string, not a dict reference) at
    # publish time.
    progress.start_run("fetch_rakuten", "日次バッチ処理")
    progress.start_stage("rakuten_prices")

    line = progress.get_snapshot_sse_line()
    assert line is not None
    event_before = json.loads(line[len("data: ") : -2])
    assert event_before["stages"][0]["status"] == "running"

    progress.finish_stage("rakuten_prices", "更新1件 / スキップ0件")

    # The already-built line/dict must be unchanged by the finish_stage()
    # call above.
    event_after = json.loads(line[len("data: ") : -2])
    assert event_after["stages"][0]["status"] == "running"


def test_update_stage_progress_ignored_after_the_stage_finished():
    progress.start_run("fetch_rakuten", "日次バッチ処理")
    progress.start_stage("rakuten_prices")
    progress.finish_stage("rakuten_prices", "更新1件 / スキップ0件")

    # A stray late progress update for a stage that's already finished
    # (e.g. a slow background thread) must not resurrect/overwrite it.
    progress.update_stage_progress("rakuten_prices", 99, 100)

    line = progress.get_snapshot_sse_line()
    event = json.loads(line[len("data: ") : -2])
    assert event["stages"][0]["status"] == "done"
    assert event["stages"][0]["current"] is None


def test_multiple_stages_are_recorded_in_order():
    progress.start_run("fetch_rakuten", "日次バッチ処理")
    progress.start_stage("rakuten_prices")
    progress.finish_stage("rakuten_prices", "更新1件")
    progress.start_stage("discovery")
    progress.finish_stage("discovery", "新規2件")
    progress.finish_run()

    line = progress.get_snapshot_sse_line()
    event = json.loads(line[len("data: ") : -2])
    assert [s["stage"] for s in event["stages"]] == ["rakuten_prices", "discovery"]
    assert all(s["status"] == "done" for s in event["stages"])
