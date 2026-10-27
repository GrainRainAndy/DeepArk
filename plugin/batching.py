"""FIFO per-session turns with a bounded debounce; independent of AstrBot."""
import asyncio
from dataclasses import dataclass, field
import time

@dataclass(eq=False)
class Ticket:
    item: object
    merge: bool
    size: int
    at: float

@dataclass(eq=False)
class Turn:
    key: str
    items: list
    waited: float
    state: object = None

@dataclass
class Session:
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    pending: list = field(default_factory=list)
    active: object = None

class TurnBuffer:
    def __init__(self, quiet=1.5, maximum=4., max_messages=32, max_chars=12000):
        self.quiet=quiet; self.maximum=maximum
        self.max_messages=max_messages; self.max_chars=max_chars
        self.sessions={}; self.closed=False

    @property
    def session_count(self):return len(self.sessions)

    def _clean(self,key,state):
        if not state.pending and state.active is None and self.sessions.get(key) is state:
            self.sessions.pop(key,None)

    async def enter(self,key,item,merge=True,size=0):
        if self.closed:return Turn(key,[item],0)
        state=self.sessions.setdefault(key,Session())
        ticket=Ticket(item,merge,size,time.monotonic())
        async with state.condition:
            state.pending.append(ticket);state.condition.notify_all()
            try:
                while True:
                    if ticket not in state.pending:return None  # merged/discarded, even during shutdown
                    if self.closed:
                        if ticket in state.pending:state.pending.remove(ticket)
                        self._clean(key,state)
                        return Turn(key,[item],time.monotonic()-ticket.at)
                    if state.active is None and state.pending[0] is ticket:
                        batch=[ticket];total=ticket.size
                        if ticket.merge:
                            for other in state.pending[1:]:
                                if not other.merge or len(batch)>=self.max_messages or total+other.size>self.max_chars:break
                                batch.append(other);total+=other.size
                        boundary=len(state.pending)>len(batch)
                        deadline=min(ticket.at+self.maximum,batch[-1].at+self.quiet)
                        delay=deadline-time.monotonic()
                        if not ticket.merge or boundary or len(batch)>=self.max_messages or delay<=0:
                            del state.pending[:len(batch)]
                            turn=Turn(key,[t.item for t in batch],time.monotonic()-ticket.at,state)
                            state.active=turn;state.condition.notify_all();return turn
                        try:await asyncio.wait_for(state.condition.wait(),delay)
                        except asyncio.TimeoutError:pass
                    else:await state.condition.wait()
            except BaseException:
                if ticket in state.pending:state.pending.remove(ticket)
                state.condition.notify_all();self._clean(key,state)
                raise

    async def finish(self,turn):
        state=turn.state
        if state is None:return
        async with state.condition:
            if state.active is turn:state.active=None
            state.condition.notify_all();self._clean(turn.key,state)

    async def discard_pending(self,key):
        state=self.sessions.get(key)
        if state is None:return
        async with state.condition:
            state.pending.clear();state.condition.notify_all();self._clean(key,state)

    async def close(self):
        self.closed=True
        for key,state in list(self.sessions.items()):
            async with state.condition:state.condition.notify_all()
