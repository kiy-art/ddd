"""In-process live-progress broadcasting for the admin "ライブダッシュボード"
(see routers/admin.py's job endpoints, frontend /admin/live).

Deliberately no external service (Pusher etc. — disallowed) and no Redis:
Render's free-tier backend runs a single uvicorn worker process (see
render.yaml's startCommand, no --workers flag), so a plain in-memory list
of subscriber queues is enough to reach every connected admin browser.
This module's state would silently stop broadcasting to every subscriber
if the backend were ever scaled to more than one process/instance — it
would need an external pub/sub (Redis etc.) at that point instead.

Every job (the daily /fetch-rakuten batch, or any of the single-action
"今すぐXX" admin buttons) is a `run` made of one or more named `stage`s,
reported through start_run -> start_stage [-> update_stage_progress]* ->
finish_stage -> ... -> finish_run. A subscriber connecting via
GET /admin/live gets the current run's full state immediately (via
get_snapshot_sse_line) so opening the dashboard mid-run isn't blank, then
every subsequent event as it happens. Queues hold pre-formatted SSE text
lines (not the run dict itself) specifically so a later mutation of the
run state can never retroactively change an event already queued for a
slow subscriber.
"""

import json
import queue
import threading
import time
import uuid

# The fixed, known set of daily-job stages, keyed by the same stage id
# every caller (routers/admin.py) uses. A run doesn't have to use all of
# these - a single-action "今すぐXX" button's run has just the one stage
# that button performs.
STAGE_LABELS = {
    "rakuten_prices": "市場価格取得中（楽天）",
    "yahoo_prices": "市場価格取得中（Yahoo!）",
    "discovery": "新商品探索中",
    "popularity": "人気ランキング同期中",
    "analysis": "買い時判定・AI説明文生成中",
    "price_alerts": "値下がり通知メール送信中",
    "x_post": "SNS投稿中",
    "title_cleanup": "商品名クレンジング・重複統合中",
}

_SUBSCRIBER_QUEUE_SIZE = 500

_lock = threading.Lock()
_subscribers: dict[str, "queue.Queue[str]"] = {}
_current_run: dict | None = None


def _sse_line(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _broadcast(event: dict) -> None:
    line = _sse_line(event)
    with _lock:
        subs = list(_subscribers.values())
    for q in subs:
        try:
            q.put_nowait(line)
        except queue.Full:
            # A stalled/very slow client - drop the event rather than
            # block the batch job itself or grow memory unboundedly.
            pass


def subscribe() -> tuple[str, "queue.Queue[str]"]:
    sub_id = uuid.uuid4().hex
    q: "queue.Queue[str]" = queue.Queue(maxsize=_SUBSCRIBER_QUEUE_SIZE)
    with _lock:
        _subscribers[sub_id] = q
    return sub_id, q


def unsubscribe(sub_id: str) -> None:
    with _lock:
        _subscribers.pop(sub_id, None)


def get_snapshot_sse_line() -> str | None:
    """The current (or, if none is running, the most recently finished)
    run's full state, pre-formatted as one SSE line - or None if no run
    has ever started in this process. Used to bootstrap a new subscriber."""
    with _lock:
        if _current_run is None:
            return None
        # A real (not shallow-aliased) copy: stages is copied too, so a
        # later mutation of the live run can't change this already-built
        # line's meaning after the fact.
        snapshot = {**_current_run, "stages": [dict(s) for s in _current_run["stages"]]}
    return _sse_line({**snapshot, "type": "snapshot"})


def start_run(job: str, job_label: str) -> None:
    global _current_run
    run = {
        "job": job,
        "job_label": job_label,
        "status": "running",
        "stage": None,
        "stage_label": None,
        "stages": [],
        "started_at": time.time(),
        "finished_at": None,
    }
    with _lock:
        _current_run = run
        snapshot = {**run, "stages": []}
    _broadcast({**snapshot, "type": "run_started"})


def start_stage(stage: str) -> None:
    label = STAGE_LABELS.get(stage, stage)
    with _lock:
        if _current_run is None:
            return
        _current_run["stage"] = stage
        _current_run["stage_label"] = label
        _current_run["stages"].append(
            {"stage": stage, "label": label, "status": "running", "current": None, "total": None, "detail": None}
        )
        snapshot = {**_current_run, "stages": [dict(s) for s in _current_run["stages"]]}
    _broadcast({**snapshot, "type": "stage_started"})


def update_stage_progress(stage: str, current: int, total: int) -> None:
    with _lock:
        if _current_run is None or _current_run.get("stage") != stage or not _current_run["stages"]:
            return
        _current_run["stages"][-1]["current"] = current
        _current_run["stages"][-1]["total"] = total
        snapshot = {**_current_run, "stages": [dict(s) for s in _current_run["stages"]]}
    _broadcast({**snapshot, "type": "stage_progress"})


def finish_stage(stage: str, detail: str) -> None:
    with _lock:
        if _current_run is None:
            return
        if _current_run["stages"] and _current_run["stages"][-1]["stage"] == stage:
            _current_run["stages"][-1]["status"] = "done"
            _current_run["stages"][-1]["detail"] = detail
        _current_run["stage"] = None
        _current_run["stage_label"] = None
        snapshot = {**_current_run, "stages": [dict(s) for s in _current_run["stages"]]}
    _broadcast({**snapshot, "type": "stage_finished"})


def finish_run(status: str = "completed") -> None:
    global _current_run
    with _lock:
        if _current_run is None:
            return
        _current_run["status"] = status
        _current_run["stage"] = None
        _current_run["stage_label"] = None
        _current_run["finished_at"] = time.time()
        snapshot = {**_current_run, "stages": [dict(s) for s in _current_run["stages"]]}
    _broadcast({**snapshot, "type": "run_finished"})
