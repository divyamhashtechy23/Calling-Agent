# Call Queue — Concurrency Control for Bolna AI Calls

When multiple leads hit the calling stage simultaneously (e.g. 50 at once), we need to respect Bolna's **max 10 concurrent calls** limit. This adds an in-memory async queue that holds back excess calls and auto-drains as calls finish.

## Proposed Changes

### Call Queue Service

#### [NEW] [call_queue_service.py](file:///d:/Calling-Agent/services/call_queue_service.py)

A new `CallQueueManager` class using Python's `asyncio.Queue` and an `asyncio.Lock`:

- **`MAX_CONCURRENT = 10`** — configurable constant
- **`active_calls`** (int) — number of calls currently in progress
- **`call_queue`** (`asyncio.Queue`) — FIFO queue of pending call requests
- **Key methods:**
  - `submit_call(request, db)` — if `active_calls < MAX`, start immediately; otherwise push onto queue. Returns a response dict with `"queued": True/False`.
  - `_start_call(request, db)` — the actual logic extracted from today's [initiate_bolna_call](file:///d:/Calling-Agent/routes/bolna_routes.py#50-128). Increments `active_calls`, creates DB record, calls Bolna.
  - `on_call_finished(execution_id)` — decrements `active_calls`, then drains the queue (starts next call if slots are available).
  - `get_status()` — returns current `active_calls` count and `queue_size` for monitoring/debugging.
- Thread-safety via `asyncio.Lock` to protect the counter + queue drain.
- A module-level singleton `call_queue_manager` so it's shared across all requests.

---

### Routes Integration

#### [MODIFY] [bolna_routes.py](file:///d:/Calling-Agent/routes/bolna_routes.py)

Two endpoints change:

1. **`POST /api/bolna/call`** (line 50–127) — instead of directly calling Bolna, delegate to `call_queue_manager.submit_call(request, db)`. The response will include a `queued` flag so the caller knows whether the call started immediately or was queued.

2. **`POST /webhook/bolna`** (line 132–227) — at the end of the `"completed"` and `"call-disconnected"` status handlers (the two terminal states), call `await call_queue_manager.on_call_finished(execution_id)` to free a slot and drain the queue.

3. **New `GET /api/bolna/queue/status`** — simple endpoint returning `active_calls` and `queue_size` for monitoring.

---

## How It Works (Flow)

```
Request arrives at POST /api/bolna/call
              │
              ▼
     ┌─ active_calls < 10? ─┐
     │ YES                   │ NO
     ▼                       ▼
  Start call            Add to queue
  active_calls++        Return {queued: true}
  Return result         (position in queue)
              │
   ─ ─ call runs ─ ─
              │
  Webhook fires (completed / call-disconnected)
              │
              ▼
        active_calls--
        Queue not empty?  →  pop & start next call
```

## Verification Plan

### Automated Test

A scratch script at `/tmp/test_call_queue.py` that:
1. Imports `CallQueueManager` directly
2. Mocks `BolnaService.initiate_call` to avoid real API calls
3. Fires 15 concurrent `submit_call` tasks
4. Asserts only 10 start immediately, 5 are queued
5. Simulates `on_call_finished` and asserts queued calls drain correctly

Run with: `python /tmp/test_call_queue.py`

### Manual Verification

Since this involves real Bolna API calls, manual testing would require:
- Sending a burst of calls via the API and observing the queue status at `GET /api/bolna/queue/status`
- Checking logs for `"Call queued"` vs `"Call started"` messages

> [!IMPORTANT]
> I'd appreciate your input on whether you'd like to manually test with real calls, or if the automated unit test is sufficient for now.
