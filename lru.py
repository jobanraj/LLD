# ==============================================================================
# FILE 3/8: lru_cache.py
# ==============================================================================
"""
PROBLEM: Design an LRU (Least Recently Used) Cache with O(1) get/put.

REQUIREMENTS MODELED:
 - get(key) -> value in O(1), marks key as most-recently-used.
 - put(key, value) in O(1), evicts least-recently-used key when capacity exceeded.

WHY THIS DESIGN (no heavyweight GoF pattern needed here — and that's a valid
interview answer!):
 - DOUBLY LINKED LIST + HASH MAP is the textbook O(1)/O(1) structure: the hash
   map gives O(1) node lookup, the linked list gives O(1) reordering
   (move-to-front) and O(1) eviction (drop from tail) — an array-based
   structure would force O(n) shifting.
 - Interviewers often SPECIFICALLY want you to justify NOT reaching for a
   "cute" pattern here — recognizing when a data-structure choice is the real
   design decision (vs. a class-hierarchy pattern) is itself a signal.

COMMON FOLLOW-UPS:
 - Thread-safety (add a lock around critical sections).
 - LFU variant (needs frequency buckets, not just recency).
 - TTL-based expiry on top of LRU.
"""


class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value
        self.prev: "_Node | None" = None
        self.next: "_Node | None" = None


class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.map: dict[int, _Node] = {}
        # sentinel head/tail avoid None-checks on every insert/remove
        self.head = _Node()
        self.tail = _Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node: _Node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_front(self, node: _Node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key: int) -> int:
        if key not in self.map:
            return -1
        node = self.map[key]
        self._remove(node)
        self._add_to_front(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        if key in self.map:
            self._remove(self.map[key])
        node = _Node(key, value)
        self.map[key] = node
        self._add_to_front(node)
        if len(self.map) > self.capacity:
            lru = self.tail.prev
            self._remove(lru)
            del self.map[lru.key]


   #freq follow up 
        class _LFUNode:
            __slots__ = ("key", "value", "freq", "prev", "next")
            def __init__(self, key=None, value=None):
                self.key = key
                self.value = value
                self.freq = 1
                self.prev: "_LFUNode | None" = None
                self.next: "_LFUNode | None" = None

        class DoublyLinkedList:
            def __init__(self):
                self.head = _LFUNode()
                self.tail = _LFUNode()
                self.head.next = self.tail
                self.tail.prev = self.head
                self._size = 0

            def append_node(self, node: _LFUNode):
                node.next = self.head.next
                node.prev = self.head
                self.head.next.prev = node
                self.head.next = node
                self._size += 1

            def remove_node(self, node: _LFUNode):
                node.prev.next = node.next
                node.next.prev = node.prev
                self._size -= 1

            def pop_tail(self) -> _LFUNode:
                node = self.tail.prev
                self.remove_node(node)
                return node

            def __len__(self):
                return self._size


        class LFUCache:
            def __init__(self, capacity: int):
                self.capacity = capacity
                self.min_freq = 0
                self.node_map: dict[int, _LFUNode] = {}
                self.freq_map: dict[int, DoublyLinkedList] = {}

            def _update_frequency(self, node: _LFUNode):
                old_freq = node.freq
                self.freq_map[old_freq].remove_node(node)
                
                # If the minimum frequency list becomes empty, increment global minimum
                if old_freq == self.min_freq and not self.freq_map[old_freq]:
                    self.min_freq += 1
                    
                node.freq += 1
                self.freq_map.setdefault(node.freq, DoublyLinkedList()).append_node(node)

            def get(self, key: int) -> int:
                if key not in self.node_map or self.capacity == 0:
                    return -1
                node = self.node_map[key]
                self._update_frequency(node)
                return node.value

            def put(self, key: int, value: int) -> None:
                if self.capacity == 0:
                    return

                if key in self.node_map:
                    node = self.node_map[key]
                    node.value = value
                    self._update_frequency(node)
                    return

                if len(self.node_map) >= self.capacity:
                    # Evict the least frequently used item (and least recently used within that frequency)
                    evict_list = self.freq_map[self.min_freq]
                    dead_node = evict_list.pop_tail()
                    del self.node_map[dead_node.key]

                new_node = _LFUNode(key, value)
                self.node_map[key] = new_node
                self.min_freq = 1
                self.freq_map.setdefault(1, DoublyLinkedList()).append_node(new_node)


   # ttl folow up
        import time
        
        class _TTLNode:
            __slots__ = ("key", "value", "expiry", "prev", "next")
            def __init__(self, key=None, value=None, expiry=0.0):
                self.key = key
                self.value = value
                self.expiry = expiry  # Unix timestamp
                self.prev: "_TTLNode | None" = None
                self.next: "_TTLNode | None" = None
        
        
        class TTLLRUCache:
            def __init__(self, capacity: int, ttl_seconds: float):
                self.capacity = capacity
                self.ttl = ttl_seconds
                self.map: dict[int, _TTLNode] = {}
                self.head = _TTLNode()
                self.tail = _TTLNode()
                self.head.next = self.tail
                self.tail.prev = self.head
        
            def _remove(self, node: _TTLNode):
                node.prev.next = node.next
                node.next.prev = node.prev
        
            def _add_to_front(self, node: _TTLNode):
                node.next = self.head.next
                node.prev = self.head
                self.head.next.prev = node
                self.head.next = node
        
            def get(self, key: int) -> int:
                if key not in self.map:
                    return -1
                
                node = self.map[key]
                # Lazy eviction check
                if time.time() > node.expiry:
                    self._remove(node)
                    del self.map[key]
                    return -1
                    
                self._remove(node)
                self._add_to_front(node)
                return node.value
        
            def put(self, key: int, value: int) -> None:
                current_time = time.time()
                expiry_time = current_time + self.ttl
        
                # FIXED BUG 1: Explicitly clear old node completely from both structures
                if key in self.map:
                    old_node = self.map[key]
                    self._remove(old_node)
                    del self.map[key]
                    
                # FIXED BUG 2: Proactively clean up expired tail items before evaluating capacity
                while self.map and time.time() > self.tail.prev.expiry:
                    expired_node = self.tail.prev
                    self._remove(expired_node)
                    del self.map[expired_node.key]
        
                # Insert new node safely
                node = _TTLNode(key, value, expiry_time)
                self.map[key] = node
                self._add_to_front(node)
        
                # Enforce hard capacity limit
                if len(self.map) > self.capacity:
                    lru = self.tail.prev
                    self._remove(lru)
                    del self.map[lru.key]

            
