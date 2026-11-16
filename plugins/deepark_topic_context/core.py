"""Bounded, transport-independent topic state. All times are monotonic seconds."""
from collections import OrderedDict, deque
from dataclasses import dataclass
import json
import math


@dataclass
class Message:
    id: str
    sender: str
    text: str
    at: float
    addressed: bool = False
    topic: str = ""
    relation: str = "unknown"


class TopicState:
    def __init__(self, now, max_messages=96):
        self.messages = deque(maxlen=max_messages)
        self.topic = ""
        self.candidate = ""
        self.votes = deque(maxlen=6)
        self.last_seen = now
        self.last_main = now
        self.idle_until = now+90
        self.last_probe = -math.inf
        self.probes = deque()
        self.revision = 0

    def observe(self, mid, sender, text, now, addressed=False):
        if not mid or not text.strip() or any(m.id == mid for m in self.messages):
            return False
        self.messages.append(Message(str(mid), str(sender), text[:1000], now, addressed))
        self.last_seen = now
        self.revision += 1
        return True

    def metrics(self, now):
        rows = [m for m in self.messages if m.topic == self.topic and m.relation == "main" and now-m.at <= 300]
        people = len({m.sender for m in rows})
        span = max(30., now-rows[0].at) if rows else 30.
        rate = len(rows)*60/span
        # Heuristic idle tolerance, not a calibrated prediction of human behavior.
        lifetime = min(900., max(90., 90+people*35+min(rate,30)*8))
        budget = min(6000, max(1200, int(1200+people*350+min(rate,30)*90)))
        return {"participants": people, "messages_per_minute": round(rate,2),
                "estimated_idle_seconds": round(lifetime), "context_chars": budget,
                "aside_weight": round(max(.1, .5/(1+people*.25+rate*.1)),2)}

    def pending(self):
        pending = [m for m in self.messages if m.relation == "unknown"]
        for m in pending[:-8]: m.relation = "aside"
        return pending[-8:]

    def payload(self):
        return {"main_topic": self.topic, "candidate_topic": self.candidate,
                "recent_context": [{"id": m.id, "text": m.text, "topic": m.topic} for m in list(self.messages)[-16:] if m.relation != "unknown"],
                "messages": [{"id": m.id, "sender": m.sender, "text": m.text} for m in self.pending()]}

    def reserve_probe(self, now, interval=10, hourly_limit=60):
        while self.probes and now-self.probes[0] >= 3600:
            self.probes.popleft()
        if not self.pending() or now-self.last_probe < interval or len(self.probes) >= hourly_limit:
            return False
        self.last_probe = now
        self.probes.append(now)
        return True

    def apply(self, raw, ids, now):
        """Validate whole response before applying any classification; never trust IDs."""
        if not isinstance(raw,str) or len(raw)>12000:
            return False
        try:
            data = json.loads(raw)
            rows = data["messages"]
            if not isinstance(rows,list) or len(rows)!=len(ids):
                return False
            valid = {}
            for row in rows:
                mid, topic, relation = row["id"], row["topic"], row["relation"]
                if not isinstance(mid,str) or mid not in ids or mid in valid:
                    return False
                if not isinstance(topic,str) or len(topic)>80 or relation not in ("main","candidate","aside","noise"):
                    return False
                if relation in ("main","candidate") and not topic.strip():
                    return False
                valid[mid]=(topic.strip(),relation)
        except (ValueError,KeyError,TypeError):
            return False
        for m in self.messages:
            if m.id not in valid or m.relation != "unknown":
                continue
            topic, relation = valid[m.id]
            if relation == "main" and self.topic and topic != self.topic:
                relation = "candidate"
            if not self.topic and relation in ("main","candidate"):
                self.topic = topic
            if topic == self.topic and relation in ("main","candidate"):
                relation = "main"
                self.last_main = m.at
            m.topic, m.relation = topic, relation
            # Votes belong to distinct observed messages; replay cannot add evidence.
            self.votes.append((topic if relation in ("main","candidate") else "",m.sender,m.at))
            if relation == "candidate":
                self.candidate = topic
                recent = [v for v in self.votes if m.at-v[2] <= 120]
                support = [v for v in recent if v[0] == topic]
                activity = self.metrics(m.at)
                required = 3 + int(activity["participants"]>=4 or activity["messages_per_minute"]>=12)
                enough = len(support)>=required and len({v[1] for v in support})>=2 or len(support)>=required+1
                if enough and len(support)/max(1,len(recent))>=.6:
                    self.topic, self.candidate = topic, ""
                    self.last_main = m.at
                    for old in self.messages:
                        if old.topic == topic and old.relation == "candidate": old.relation="main"
                    self.votes.clear()
            if m.topic == self.topic and m.relation == "main":
                self.idle_until = m.at+self.metrics(m.at)["estimated_idle_seconds"]
        self.revision += 1
        return True

    def context(self, now, addressed_id=None, reserve_chars=0):
        metrics = self.metrics(now)
        active = bool(self.topic) and now <= self.idle_until
        metrics["estimated_remaining_seconds"] = max(0,round(self.idle_until-now))
        main = [m for m in self.messages if active and m.topic == self.topic and m.relation == "main"]
        # Asides remain available; current explicit request gets a separate priority lane.
        other = [m for m in self.messages if m not in main and now-m.at<=180][-4:]
        focus = next((m for m in self.messages if m.id==addressed_id),None)
        cap = max(300, metrics["context_chars"]-max(0,reserve_chars))
        selected, used = [], 0
        aside_cap = max(200, int(cap*metrics["aside_weight"]))
        # Reserve space for recent asides even during a high-volume main topic.
        aside_rows = []
        aside_used = 0
        for m in reversed(other):
            if m is focus: continue
            remaining = aside_cap-aside_used
            if remaining > 0:
                limit = min(len(m.text), remaining)
                aside_rows.append((m,limit)); aside_used += limit
        ordered = ([(focus,len(focus.text))] if focus else []) + aside_rows + [(m,len(m.text)) for m in reversed(main)]
        for m,limit in ordered:
            if m is None or any(x["id"]==m.id for x in selected): continue
            text = m.text[:max(0,min(limit,cap-used))]
            if not text: break
            selected.append({"id":m.id,"sender":m.sender,"text":text,
                             "relation":"addressed" if m is focus else ("aside" if m.relation=="main" and m.topic!=self.topic else m.relation),
                             "topic":m.topic,"at":m.at})
            used += len(text)
        selected.sort(key=lambda x:x["at"])
        return {"main_topic":self.topic if active else "", "candidate_topic":self.candidate if active else "",
                "metrics":metrics,"messages":selected,"addressed_id":addressed_id}


class TopicStore:
    def __init__(self, max_sessions=64, ttl=1800):
        self.sessions=OrderedDict()
        self.max_sessions=max(1,min(256,int(max_sessions)))
        self.ttl=max(60,min(7200,float(ttl)))

    def get(self, scope, now):
        for key in list(self.sessions):
            if now-self.sessions[key].last_seen>self.ttl: del self.sessions[key]
        if scope not in self.sessions:
            while len(self.sessions)>=self.max_sessions: self.sessions.popitem(last=False)
            self.sessions[scope]=TopicState(now)
        self.sessions.move_to_end(scope)
        return self.sessions[scope]

    def forget(self, scope):
        self.sessions.pop(scope,None)
