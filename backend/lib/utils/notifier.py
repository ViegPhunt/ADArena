import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AttackNotifier:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_queue())
        logger.info("AttackNotifier started")
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AttackNotifier stopped")
    
    async def notify(
        self,
        attacker_id: int,
        attacker_name: str,
        victim_id: int,
        victim_name: str,
        task_id: int,
        task_name: str,
        points: float,
    ):
        notification = {
            "attacker_id": attacker_id,
            "attacker_name": attacker_name,
            "victim_id": victim_id,
            "victim_name": victim_name,
            "task_id": task_id,
            "task_name": task_name,
            "points": round(points, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            self._queue.put_nowait(notification)
            logger.debug(f"Queued notification: {attacker_name} → {victim_name} (+{points:.2f})")
        except asyncio.QueueFull:
            logger.warning("Notification queue full, dropping notification")
    
    async def _process_queue(self):
        logger.info("Notification processor started")
        
        while self._running:
            try:
                notification = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=3.0
                )
                
                await self._broadcast(notification)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing notification: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info("Notification processor stopped")
    
    async def _broadcast(self, notification: Dict[str, Any]):
        try:
            from api.events import manager
            
            await manager.broadcast_live_event({
                "event": "flag_stolen",
                "data": notification
            })
            
            logger.debug(
                f"Broadcasted: {notification['attacker_name']} stole from "
                f"{notification['victim_name']} (+{notification['points']})"
            )
            
        except Exception as e:
            logger.error(f"Error broadcasting notification: {e}")


_notifier: Optional[AttackNotifier] = None


def get_notifier() -> AttackNotifier:
    global _notifier
    if _notifier is None:
        _notifier = AttackNotifier()
    return _notifier


async def start_notifier():
    notifier = get_notifier()
    await notifier.start()


async def stop_notifier():
    notifier = get_notifier()
    await notifier.stop()