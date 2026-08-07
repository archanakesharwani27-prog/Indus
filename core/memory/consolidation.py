"""
MemoryConsolidator - Background job to consolidate memories into semantic memory
"""

import os
import json
import threading
import time
import schedule
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from core.memory import Memory
from core.memory.semantic import SemanticMemory, get_semantic_memory
from core.llm_provider import LLMProvider


@dataclass
class ConsolidationJob:
    """Represents a consolidation job."""
    id: str
    status: str  # pending, running, completed, failed
    started_at: str
    completed_at: Optional[str] = None
    items_processed: int = 0
    items_failed: int = 0
    error: Optional[str] = None


class MemoryConsolidator:
    """Background consolidation of raw memories into semantic memory."""
    
    def __init__(
        self,
        memory: Memory,
        semantic_memory: SemanticMemory,
        llm_provider: Optional[LLMProvider] = None,
        batch_size: int = 50,
        interval_minutes: int = 60,
        max_workers: int = 2
    ):
        self.memory = memory
        self.semantic_memory = semantic_memory
        self.llm_provider = llm_provider
        self.batch_size = batch_size
        self.interval_minutes = interval_minutes
        self.max_workers = max_workers
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._scheduler_thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, ConsolidationJob] = {}
        self._lock = threading.Lock()
        self._last_consolidated_id = 0
    
    def start(self):
        """Start the consolidation scheduler."""
        if self._running:
            return
        
        self._running = True
        
        # Run initial consolidation
        self._executor.submit(self._run_consolidation)
        
        # Schedule periodic consolidation
        def run_scheduler():
            schedule.every(self.interval_minutes).minutes.do(
                lambda: self._executor.submit(self._run_consolidation)
            )
            while self._running:
                schedule.run_pending()
                time.sleep(60)
        
        self._scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self._scheduler_thread.start()
        
        print(f"MemoryConsolidator started (interval: {self.interval_minutes} min)")
    
    def stop(self):
        """Stop the consolidation scheduler."""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        self._executor.shutdown(wait=True)
        print("MemoryConsolidator stopped")
    
    def _run_consolidation(self):
        """Run a single consolidation cycle."""
        job_id = f"consolidation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job = ConsolidationJob(
            id=job_id,
            status="running",
            started_at=datetime.now().isoformat()
        )
        
        with self._lock:
            self._jobs[job_id] = job
        
        try:
            # Get unconsolidated messages
            messages = self._get_unconsolidated_messages()
            
            if not messages:
                job.status = "completed"
                job.completed_at = datetime.now().isoformat()
                with self._lock:
                    self._jobs[job_id] = job
                return
            
            # Process in batches
            for i in range(0, len(messages), self.batch_size):
                batch = messages[i:i + self.batch_size]
                self._process_batch(batch, job)
            
            job.status = "completed"
            job.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now().isoformat()
        
        with self._lock:
            self._jobs[job_id] = job
    
    def _get_unconsolidated_messages(self) -> List[Dict[str, Any]]:
        """Get messages that haven't been consolidated yet."""
        conn = sqlite3.connect(self.memory.db_path)
        conn.row_factory = sqlite3.Row
        
        # Get messages after last consolidated ID
        rows = conn.execute("""
            SELECT id, role, content, timestamp FROM messages
            WHERE id > ? ORDER BY id ASC
        """, (self._last_consolidated_id,)).fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def _process_batch(self, messages: List[Dict[str, Any]], job: ConsolidationJob):
        """Process a batch of messages into semantic memory."""
        
        # Group by conversation turns (user + assistant pairs)
        turns = []
        current_user = None
        
        for msg in messages:
            if msg["role"] == "user":
                current_user = msg
            elif msg["role"] == "assistant" and current_user:
                turns.append((current_user, msg))
                current_user = None
        
        # Consolidate each turn
        for user_msg, assistant_msg in turns:
            try:
                self.semantic_memory.add_conversation(
                    user_message=user_msg["content"],
                    assistant_response=assistant_msg["content"],
                    metadata={
                        "user_msg_id": user_msg["id"],
                        "assistant_msg_id": assistant_msg["id"],
                        "timestamp": user_msg["timestamp"]
                    }
                )
                job.items_processed += 1
                
                # Update last consolidated ID
                self._last_consolidated_id = max(
                    self._last_consolidated_id,
                    user_msg["id"],
                    assistant_msg["id"]
                )
                
            except Exception as e:
                job.items_failed += 1
                print(f"Consolidation failed for turn: {e}")
    
    def force_consolidation(self, since_id: int = 0) -> ConsolidationJob:
        """Force immediate consolidation of messages since given ID."""
        self._last_consolidated_id = since_id
        future = self._executor.submit(self._run_consolidation)
        return future.result()
    
    def get_job_status(self, job_id: str) -> Optional[ConsolidationJob]:
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_recent_jobs(self, limit: int = 10) -> List[ConsolidationJob]:
        with self._lock:
            jobs = list(self._jobs.values())
            jobs.sort(key=lambda j: j.started_at, reverse=True)
            return jobs[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_jobs = len(self._jobs)
            completed = sum(1 for j in self._jobs.values() if j.status == "completed")
            failed = sum(1 for j in self._jobs.values() if j.status == "failed")
            running = sum(1 for j in self._jobs.values() if j.status == "running")
            total_processed = sum(j.items_processed for j in self._jobs.values())
            total_failed = sum(j.items_failed for j in self._jobs.values())
        
        return {
            "total_jobs": total_jobs,
            "completed": completed,
            "failed": failed,
            "running": running,
            "total_items_processed": total_processed,
            "total_items_failed": total_failed,
            "last_consolidated_id": self._last_consolidated_id,
            "is_running": self._running
        }


# Global instance
_consolidator: Optional[MemoryConsolidator] = None


def get_consolidator(
    memory: Memory,
    semantic_memory: SemanticMemory,
    llm_provider: Optional[LLMProvider] = None,
    **kwargs
) -> MemoryConsolidator:
    global _consolidator
    if _consolidator is None:
        _consolidator = MemoryConsolidator(
            memory=memory,
            semantic_memory=semantic_memory,
            llm_provider=llm_provider,
            **kwargs
        )
    return _consolidator


import sqlite3