import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

class Event:
    def __init__(self, topic: str, payload: Any):
        self.topic = topic
        self.payload = payload

class EventBus:
    def __init__(self, max_workers: int = 4):
        self.subscribers = defaultdict(list)
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def subscribe(self, topic: str, handler: Callable[[Event], None]):
        with self.lock:
            self.subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable[[Event], None]):
        with self.lock:
            if handler in self.subscribers[topic]:
                self.subscribers[topic].remove(handler)

    def publish(self, event: Event):
        with self.lock:
            handlers = list(self.subscribers[event.topic])
        for handler in handlers:
            self.executor.submit(self._safe_execute, handler, event)

    def _safe_execute(self, handler: Callable[[Event], None], event: Event):
        try:
            handler(event)
        except Exception as e:
            print(f"Error processing event on topic '{event.topic}': {e}")
