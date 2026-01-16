"""Action coordination system using Redis Pub/Sub and streams.

Provides three main functions:
1. CHECK completion signaling - Notifies PUT/GET when CHECK finishes
2. Action result tracking - Stores per-action results in Redis
3. Round monitoring - Aggregates results for health checks

Architecture:
- Redis Pub/Sub: Real-time CHECK completion notifications
- Redis Hash: Per-team-task-round result storage (10min TTL)
- Redis Stream: Round-wide event log (10k events max)

Key Pattern:
- check_complete:{round}:{team_id}:{task_id} - CHECK status code
- check_done:{round}:{team_id}:{task_id} - Pub/Sub channel
- action_result:{round}:{team_id}:{task_id}:{action} - Individual result
- round_tracking:{round}:{team_id}:{task_id} - All actions hash
- action_stream:{round} - Round event stream
"""
import asyncio
import logging
import json
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

from lib.repositories.utils import get_redis_client

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result of a single action (CHECK/PUT/GET).
    
    Attributes:
        action: Action type ('check', 'put', 'get')
        team_id: Target team ID
        task_id: Target task ID
        round: Game round number
        status: Status string (UP, DOWN, MUMBLE, CORRUPT, CHECK_FAILED)
        status_code: Numeric status code (101-110)
        public_message: Public-facing message
        private_message: Admin-only debug message
        timestamp: Unix timestamp from event loop
        flag: Optional flag string (PUT actions only)
    """
    action: str
    team_id: int
    task_id: int
    round: int
    status: str
    status_code: int
    public_message: str
    private_message: str
    timestamp: float
    flag: Optional[str] = None


class ActionCoordinator:
    """Coordinates action execution and tracks results across the system.
    
    Singleton instance managed via get_coordinator() function.
    Maintains Redis connection for Pub/Sub and result storage.
    
    Key Methods:
    - signal_check_complete(): Notify PUT/GET that CHECK finished
    - wait_for_check(): Block until CHECK completes (with timeout)
    - record_action_result(): Store action result in Redis
    - get_round_summary(): Aggregate statistics for monitoring
    """
    def __init__(self):
        self.redis = None
        
    async def initialize(self):
        """Initialize Redis connection."""
        self.redis = get_redis_client()
        logger.info("ActionCoordinator initialized")
    
    # ==================== CHECK Completion Signaling ====================
    
    def _get_check_key(self, team_id: int, task_id: int, round_num: int) -> str:
        """Generate Redis key for CHECK status storage."""
        return f"check_complete:{round_num}:{team_id}:{task_id}"
    
    def _get_check_channel(self, team_id: int, task_id: int, round_num: int) -> str:
        """Generate Redis Pub/Sub channel name for CHECK notifications."""
        return f"check_done:{round_num}:{team_id}:{task_id}"
    
    async def signal_check_complete(self, team_id: int, task_id: int, round_num: int, status_code: int):
        """Signal that CHECK action has completed.
        
        Stores result in Redis with 5-minute TTL and publishes to Pub/Sub channel.
        Called by check_action() after database commit.
        
        Args:
            team_id: Team ID
            task_id: Task ID
            round_num: Round number
            status_code: CHECK status code (101-110)
        """
        key = self._get_check_key(team_id, task_id, round_num)
        channel = self._get_check_channel(team_id, task_id, round_num)
        
        # Store status with TTL for DB fallback
        await self.redis.setex(key, 300, str(status_code))
        
        # Publish to Pub/Sub for real-time notifications
        await self.redis.publish(channel, str(status_code))
        
        logger.debug(f"Signaled CHECK complete: team={team_id}, task={task_id}, round={round_num}, status={status_code}")
    
    async def wait_for_check(
        self, 
        team_id: int, 
        task_id: int, 
        round_num: int, 
        timeout: float = 60.0
    ) -> Optional[int]:
        """Wait for CHECK action to complete via Pub/Sub.
        
        Strategy:
        1. Check if result already exists in Redis (fast path)
        2. Subscribe to Pub/Sub channel and wait for signal
        3. Timeout after specified seconds
        
        Called by put_action() and get_action() to enforce dependencies.
        
        Args:
            team_id: Team ID
            task_id: Task ID
            round_num: Round number
            timeout: Maximum wait time in seconds (default: 60)
            
        Returns:
            CHECK status code (101-110), or None if timeout
        """
        key = self._get_check_key(team_id, task_id, round_num)
        
        # Fast path: Check if already completed
        existing = await self.redis.get(key)
        if existing:
            return int(existing)

        # Slow path: Subscribe and wait
        channel = self._get_check_channel(team_id, task_id, round_num)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    status_code = int(message['data'])
                    logger.debug(f"Received CHECK signal: team={team_id}, task={task_id}, status={status_code}")
                    return status_code
                
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.warning(
                        f"CHECK timeout after {timeout}s: team={team_id}, task={task_id}, round={round_num}"
                    )
                    return None
        
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    
    # ==================== Action Result Tracking ====================
    
    def _get_result_key(self, team_id: int, task_id: int, round_num: int, action: str) -> str:
        """Generate Redis key for individual action result."""
        return f"action_result:{round_num}:{team_id}:{task_id}:{action}"
    
    def _get_round_key(self, team_id: int, task_id: int, round_num: int) -> str:
        """Generate Redis hash key for all actions in a team-task-round."""
        return f"round_tracking:{round_num}:{team_id}:{task_id}"
    
    async def record_action_result(self, result: ActionResult):
        """Store action result in Redis for monitoring.
        
        Stores in three locations:
        1. Individual key (action_result:*) - For direct lookups
        2. Round hash (round_tracking:*) - For team-task-round aggregation
        3. Round stream (action_stream:*) - For statistics and monitoring
        
        All entries have 10-minute TTL except stream (10k events max).
        
        Args:
            result: ActionResult dataclass instance
        """
        key = self._get_result_key(result.team_id, result.task_id, result.round, result.action)
        data = json.dumps(asdict(result))
        await self.redis.setex(key, 600, data)
        
        round_key = self._get_round_key(result.team_id, result.task_id, result.round)
        await self.redis.hset(round_key, result.action, data)
        await self.redis.expire(round_key, 600)
        
        # Add to stream for monitoring and statistics
        await self.redis.xadd(
            f"action_stream:{result.round}",
            asdict(result),
            maxlen=10000
        )
        
        logger.info(
            f"Recorded {result.action.upper()} result: "
            f"team={result.team_id}, task={result.task_id}, "
            f"round={result.round}, status={result.status}"
        )
    
    async def get_round_results(
        self, 
        team_id: int, 
        task_id: int, 
        round_num: int
    ) -> Dict[str, ActionResult]:
        """Retrieve all action results for a team-task-round combination.
        
        Args:
            team_id: Team ID
            task_id: Task ID
            round_num: Round number
            
        Returns:
            Dictionary mapping action names to ActionResult objects
        """
        round_key = self._get_round_key(team_id, task_id, round_num)
        data = await self.redis.hgetall(round_key)
        
        results = {}
        for action, json_data in data.items():
            result_dict = json.loads(json_data)
            results[action] = ActionResult(**result_dict)
        
        return results
    
    async def get_round_summary(self, round_num: int) -> Dict:
        """Generate summary statistics for an entire round.
        
        Aggregates all actions from action_stream to provide:
        - Total action count
        - Breakdown by action type (check/put/get)
        - Breakdown by status (UP/DOWN/MUMBLE/etc)
        - List of error events
        
        Used by round_monitor for health checks.
        
        Args:
            round_num: Round number to summarize
            
        Returns:
            Dictionary with round statistics
        """
        events = await self.redis.xrange(f"action_stream:{round_num}")
        
        summary = {
            'round': round_num,
            'total_actions': len(events),
            'by_status': {},
            'by_action': {'check': 0, 'put': 0, 'get': 0},
            'errors': [],
        }
        
        for event_id, event_data in events:
            action = event_data.get('action', '').lower()
            status = event_data.get('status', 'UNKNOWN')
            
            if action in summary['by_action']:
                summary['by_action'][action] += 1
            
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
            
            if status in ['DOWN', 'CHECK_FAILED', 'MUMBLE', 'CORRUPT']:
                summary['errors'].append({
                    'team_id': event_data.get('team_id'),
                    'task_id': event_data.get('task_id'),
                    'action': action,
                    'status': status,
                    'message': event_data.get('public_message', ''),
                })
        
        return summary
    
    
    async def is_round_complete(self, team_id: int, task_id: int, round_num: int) -> bool:
        """Check if all expected actions completed for a team-task-round.
        
        Currently simplified: Returns True if CHECK exists.
        TODO: Compare against expected PUT/GET counts from task.puts/task.gets
        
        Args:
            team_id: Team ID
            task_id: Task ID
            round_num: Round number
            
        Returns:
            True if round is considered complete
        """
        results = await self.get_round_results(team_id, task_id, round_num)
        
        if 'check' not in results:
            return False
        
        # TODO: Check expected number of PUTs/GETs from task config
        return True


_coordinator: Optional[ActionCoordinator] = None


async def get_coordinator() -> ActionCoordinator:
    """Get or create the global ActionCoordinator singleton.
    
    Thread-safe singleton pattern using global variable.
    Initializes Redis connection on first call.
    
    Returns:
        Initialized ActionCoordinator instance
    """
    global _coordinator
    if _coordinator is None:
        _coordinator = ActionCoordinator()
        await _coordinator.initialize()
    return _coordinator


async def close_coordinator():
    """Close coordinator and cleanup Redis connection.
    
    Should be called during application shutdown.
    Safe to call multiple times.
    """
    global _coordinator
    if _coordinator is not None:
        if _coordinator.redis:
            try:
                await _coordinator.redis.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")
        _coordinator = None
        logger.info("ActionCoordinator closed")