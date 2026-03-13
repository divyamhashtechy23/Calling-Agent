"""
CallQueueManager - Controls how many AI calls run at the same time.

Problem: Bolna allows max 10 concurrent calls.
Solution: If 10 calls are already running, new requests wait in a queue.
When a call finishes, the next queued call starts automatically.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from collections import deque

logger = logging.getLogger(__name__)

MAX_CONCURRENT_CALLS = 10  # Bolna plan limit


class CallQueueManager:
    """
    In-memory call queue with concurrency control

    - Allows up to MAX_CONCURRENT_CALLS to run simultaneously
    - Excess calls wait in a FIFO queue
    - When a call finishes, the next queued call starts automatically
    """

    def __init__(self):
        self.active_calls: int = 0
        self.call_queue: deque = deque()
        self._lock = asyncio.Lock()
        logger.info("CallQueueManager initialized | max_concurrent=%d", MAX_CONCURRENT_CALLS)

    async def submit_call(
        self,
        call_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Submit a call request.
        - If there's room -> start it immediately
        - If at capacity -> add to queue for later

        Args:
            call_request: Dict containing all the data needed to make the call
                          (leadId, leadName, leadPhone, agent_id, etc.)

        Returns:
            Dict with status info: was it started or queued?
        """
        async with self._lock:
            # -- Room available? Start right away --
            if self.active_calls < MAX_CONCURRENT_CALLS:
                self.active_calls += 1
                logger.info(
                    "Call started immediately | lead=%s | active=%d/%d",
                    call_request.get("leadName", "?"),
                    self.active_calls,
                    MAX_CONCURRENT_CALLS,
                )
                return {
                    "queued": False,
                    "active_calls": self.active_calls,
                    "queue_position": 0,
                    "message": "Call started immediately.",
                    "call_request": call_request,
                }

            # -- No room? Add to queue --
            self.call_queue.append(call_request)
            position = len(self.call_queue)
            logger.info(
                "Call queued | lead=%s | position=%d | active=%d/%d",
                call_request.get("leadName", "?"),
                position,
                self.active_calls,
                MAX_CONCURRENT_CALLS,
            )
            return {
                "queued": True,
                "active_calls": self.active_calls,
                "queue_position": position,
                "message": f"All {MAX_CONCURRENT_CALLS} slots full. Queued at position {position}.",
                "call_request": call_request,
            }

    async def on_call_finished(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Called when a call completes (via webhook).
        Frees one slot, and if there are queued calls, starts the next one.

        Args:
            execution_id: The Bolna execution ID of the finished call

        Returns:
            The next call_request that was started, or None if queue was empty
        """
        async with self._lock:
            # -- Free the slot --
            if self.active_calls > 0:
                self.active_calls -= 1

            logger.info(
                "Call finished | execution_id=%s | active=%d/%d | queued=%d",
                execution_id,
                self.active_calls,
                MAX_CONCURRENT_CALLS,
                len(self.call_queue),
            )

            # -- Anyone waiting? Start the next call --
            if self.call_queue and self.active_calls < MAX_CONCURRENT_CALLS:
                next_request = self.call_queue.popleft()  # FIFO: first in, first out
                self.active_calls += 1
                logger.info(
                    "Dequeued next call | lead=%s | active=%d/%d | remaining_queue=%d",
                    next_request.get("leadName", "?"),
                    self.active_calls,
                    MAX_CONCURRENT_CALLS,
                    len(self.call_queue),
                )
                return next_request

            return None

    def get_status(self) -> Dict[str, Any]:
        """Returns current queue state - useful for monitoring/debugging."""
        return {
            "active_calls": self.active_calls,
            "max_concurrent": MAX_CONCURRENT_CALLS,
            "queue_size": len(self.call_queue),
            "queued_leads": [
                req.get("leadName", "?") for req in self.call_queue
            ],
        }


# -- Singleton (module-level, OUTSIDE the class) --
# One instance shared across all requests in this process.
call_queue_manager = CallQueueManager()
