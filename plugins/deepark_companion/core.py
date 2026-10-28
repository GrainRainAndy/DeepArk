"""Local, scoped memory and durable unsolicited-message budgets. No network I/O."""
import datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid
from zoneinfo import ZoneInfo


SENSITIVE = re.compile(r'sk-[\w-]{12,}|Bearer\s+\S{12,}|(?:api.?key|access.?token|密码|口令|身份证|住址|电话)\s*[:：=是]?|(?<!\d)1[3-9]\d{9}(?!\d)|忽略.{0,12}(?:规则|指令)|泄露.{0,8}(?:提示词|密钥)|(?:system|developer)\s*:', re.I)


def safe_text(text, limit=400):
    if not isinstance(text, str) or not text.strip() or SENSITIVE.search(text):
        return None
    return text.strip()[:limit]


class Store:
    def __init__(self, path, policy=None):
        self.policy=policy if policy is not None else {}
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path, timeout=10)
        os.chmod(path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS memories (
          scope TEXT, subject TEXT, key TEXT, value TEXT, source TEXT,
          updated REAL, expires REAL, PRIMARY KEY(scope,subject,key));
        CREATE TABLE IF NOT EXISTS controls (
          scope TEXT, subject TEXT, generation INTEGER DEFAULT 0,
          blocked INTEGER DEFAULT 0, PRIMARY KEY(scope,subject));
        CREATE TABLE IF NOT EXISTS history (
          scope TEXT, subject TEXT, message_id TEXT, text TEXT, at REAL,
          PRIMARY KEY(scope,message_id));
        CREATE TABLE IF NOT EXISTS sessions (
          scope TEXT PRIMARY KEY, last_human REAL DEFAULT 0, last_bot REAL DEFAULT 0,
          last_unsolicited REAL DEFAULT 0, last_idle REAL DEFAULT 0,
          day TEXT DEFAULT '', idle_count INTEGER DEFAULT 0,
          interject_count INTEGER DEFAULT 0, muted INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS tombstones (
          scope TEXT,subject TEXT,key TEXT,PRIMARY KEY(scope,subject,key));
        CREATE TABLE IF NOT EXISTS revisions (scope TEXT PRIMARY KEY, revision INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS followups (scope TEXT PRIMARY KEY, started REAL, last_bot REAL, count INTEGER DEFAULT 0, last_attempt REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS reply_reservations (scope TEXT, at REAL);
        CREATE INDEX IF NOT EXISTS reply_reservations_scope_at ON reply_reservations(scope,at);
        CREATE TABLE IF NOT EXISTS followup_probes (scope TEXT PRIMARY KEY, started REAL, count INTEGER, last_attempt REAL);
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    def generation(self, scope, subject):
        r = self.db.execute('SELECT generation FROM controls WHERE scope=? AND subject=?', (scope,subject)).fetchone()
        return r[0] if r else 0

    def remember(self, scope, subject, key, value, source, now, ttl=90*86400, generation=None, explicit=False):
        if not isinstance(key,str) or len(key.strip())>60:return False
        key = safe_text(key, 60)
        value = safe_text(value, 240)
        source = safe_text(source, 300)
        if not key or not value or not source:
            return False
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            control = self.db.execute('SELECT generation,blocked FROM controls WHERE scope=? AND subject=?', (scope,subject)).fetchone()
            current, blocked = (control[0],control[1]) if control else (0,0)
            tombstone = self.db.execute('SELECT 1 FROM tombstones WHERE scope=? AND subject=? AND key=?',(scope,subject,key)).fetchone()
            if generation is not None and generation != current:
                return False
            if (blocked or tombstone) and not explicit:
                return False
            if explicit:
                self.db.execute('INSERT INTO controls(scope,subject,generation) VALUES (?,?,1) ON CONFLICT(scope,subject) DO UPDATE SET generation=generation+1',(scope,subject))
                self.db.execute('INSERT INTO revisions VALUES (?,1) ON CONFLICT(scope) DO UPDATE SET revision=revision+1',(scope,))
                self.db.execute('DELETE FROM tombstones WHERE scope=? AND subject=? AND key=?',(scope,subject,key))
            self.db.execute('INSERT OR REPLACE INTO memories VALUES (?,?,?,?,?,?,?)', (scope,subject,key,value,source,now,now+max(60,min(ttl,180*86400))))
        return True

    def recall(self, scope, subject, query, now, budget=1200):
        rows = self.db.execute('SELECT key,value,source,updated FROM memories WHERE scope=? AND subject=? AND expires>? ORDER BY updated DESC', (scope,subject,now)).fetchall()
        tokens = set(re.findall(r'[\u4e00-\u9fff]|[a-z0-9]+',query.lower()))
        rows = sorted(rows,key=lambda r:len(tokens.intersection(set(re.findall(r'[\u4e00-\u9fff]|[a-z0-9]+', (r['key']+r['value']).lower())))),reverse=True)
        out=[]
        for r in rows:
            size=len(r['key'])+len(r['value'])
            if size>budget:continue
            out.append(dict(r));budget-=size
            if len(out)>=8:break
        return out

    def forget(self, scope, subject, key, now):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            self.db.execute('INSERT INTO revisions VALUES (?,1) ON CONFLICT(scope) DO UPDATE SET revision=revision+1',(scope,))
            self.db.execute('INSERT INTO controls(scope,subject,generation,blocked) VALUES (?,?,1,?) ON CONFLICT(scope,subject) DO UPDATE SET generation=generation+1,blocked=MAX(blocked,excluded.blocked)', (scope,subject,int(key is None)))
            if key is None:
                self.db.execute('DELETE FROM memories WHERE scope=? AND subject=?',(scope,subject))
            else:
                self.db.execute('DELETE FROM memories WHERE scope=? AND subject=? AND key=?',(scope,subject,key))
                self.db.execute('INSERT OR IGNORE INTO tombstones VALUES (?,?,?)',(scope,subject,key))
            # Clear this person's rolling context as well, avoiding re-extraction.
            self.db.execute('DELETE FROM history WHERE scope=? AND subject=?',(scope,subject))
            self.db.execute('DELETE FROM history WHERE scope=? AND subject=?',(scope,'@bot'))

    def revision(self, scope):
        row=self.db.execute('SELECT revision FROM revisions WHERE scope=?',(scope,)).fetchone()
        return row[0] if row else 0

    def observe(self, scope, subject, message_id, text, now):
        text=safe_text(text,600)
        if not text or not message_id:return False
        with self.db:
            result=self.db.execute('INSERT OR IGNORE INTO history VALUES (?,?,?,?,?)',(scope,subject,str(message_id),text,now))
            if result.rowcount == 0:return False
            self.db.execute('INSERT INTO sessions(scope,last_human) VALUES (?,?) ON CONFLICT(scope) DO UPDATE SET last_human=MAX(last_human,excluded.last_human)',(scope,now))
            self.db.execute('DELETE FROM history WHERE at<?',(now-86400,))
            self.db.execute('DELETE FROM memories WHERE expires<=?',(now,))
            self.db.execute('DELETE FROM history WHERE scope=? AND message_id NOT IN (SELECT message_id FROM history WHERE scope=? ORDER BY at DESC LIMIT 60)',(scope,scope))
        return True

    def history(self, scope, now):
        return [dict(r) for r in self.db.execute('SELECT subject,text,at FROM history WHERE scope=? AND at>? ORDER BY at DESC LIMIT 20',(scope,now-86400))][::-1]

    def mute(self, scope, enabled):
        with self.db:
            self.db.execute('INSERT INTO sessions(scope,muted) VALUES (?,?) ON CONFLICT(scope) DO UPDATE SET muted=excluded.muted',(scope,int(enabled)))

    def bot_spoke(self, scope, now):
        with self.db:
            self.db.execute('UPDATE sessions SET last_bot=? WHERE scope=?',(now,scope))

    def record_bot(self, scope, text, now, continuation=False):
        text=safe_text(text,600)
        if not text:return
        with self.db:
            self.db.execute('INSERT INTO history VALUES (?,?,?,?,?)',(scope,'@bot',str(uuid.uuid4()),text,now))
            self.db.execute('DELETE FROM history WHERE at<?',(now-86400,))
        self.bot_spoke(scope,now)
        with self.db:
            if continuation:
                self.db.execute('UPDATE followups SET last_bot=? WHERE scope=?',(now,scope))
            else:
                self.db.execute('INSERT INTO followups VALUES (?,?,?,0,0) ON CONFLICT(scope) DO UPDATE SET started=excluded.started,last_bot=excluded.last_bot,count=0,last_attempt=0',(scope,now,now))

    def followup_ready(self,scope,now):
        row=self.db.execute('SELECT * FROM followups WHERE scope=?',(scope,)).fetchone()
        muted=self.db.execute('SELECT muted FROM sessions WHERE scope=?',(scope,)).fetchone()
        return bool(row and not (muted and muted[0]) and 0<=now-row['last_bot']<=self.setting('followup_window_seconds',120,15,300) and now-row['started']<=600 and row['count']<self.setting('followup_burst_limit',3,0,60) and now-row['last_attempt']>=5)

    def reserve_followup(self,scope,now):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if not self.followup_ready(scope,now):return False
            self.db.execute('UPDATE followups SET count=count+1,last_attempt=? WHERE scope=?',(now,scope))
        return True

    def reserve_followup_probe(self,scope,now,min_gap=5):
        with self.db:
            row=self.db.execute('SELECT * FROM followup_probes WHERE scope=?',(scope,)).fetchone()
            started=row['started'] if row and now-row['started']<3600 else now
            count=row['count'] if row and started==row['started'] else 0
            if row and now-row['last_attempt']<min_gap:return False
            if count>=self.setting('participation_probe_hourly_limit',300,0,300):return False
            self.db.execute('INSERT OR REPLACE INTO followup_probes VALUES (?,?,?,?)',(scope,started,count+1,now))
        return True

    def reserve_reply(self,scope,now):
        """Rolling-hour reservation per logical AI reply; failed sends stay counted."""
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            self.db.execute('DELETE FROM reply_reservations WHERE at<=?',(now-3600,))
            count=self.db.execute('SELECT COUNT(*) FROM reply_reservations WHERE scope=?',(scope,)).fetchone()[0]
            if count>=self.setting('group_reply_hourly_limit',300,0,300):return False
            self.db.execute('INSERT INTO reply_reservations VALUES (?,?)',(scope,now))
        return True

    def can_deliver(self, scope, now):
        local=datetime.datetime.fromtimestamp(now,ZoneInfo('Asia/Shanghai'))
        row=self.db.execute('SELECT * FROM sessions WHERE scope=?',(scope,)).fetchone()
        return bool(row and not row['muted'] and self.in_hours(local.hour) and row['last_bot']<row['last_unsolicited'] and now-row['last_unsolicited']<90)

    def setting(self,name,default,low,high):
        try:return max(low,min(high,int(self.policy.get(name,default))))
        except (TypeError,ValueError):return default

    def in_hours(self,hour):
        start=self.setting('active_start_hour',9,0,23)
        end=self.setting('active_end_hour',23,1,24)
        return start<=hour<end if start<end else (hour>=start or hour<end) if start>end else False

    def scopes(self):
        return [r[0] for r in self.db.execute('SELECT scope FROM sessions')]

    def reserve(self, scope, mode, now, check_only=False):
        """Reserve BEFORE generation/send; failed attempts consume budget (fail closed)."""
        if mode not in ('idle','interject'):return False
        local=datetime.datetime.fromtimestamp(now,ZoneInfo('Asia/Shanghai'))
        if not self.in_hours(local.hour):return False
        day=local.date().isoformat()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row=self.db.execute('SELECT * FROM sessions WHERE scope=?',(scope,)).fetchone()
            if not row or row['muted'] or not row['last_human']:return False
            if now-row['last_bot']<self.setting('bot_quiet_seconds',180,60,86400) or now-row['last_unsolicited']<self.setting('unsolicited_gap_seconds',600,60,86400):return False
            idle_count=row['idle_count'] if row['day']==day else 0
            interject_count=row['interject_count'] if row['day']==day else 0
            if mode=='idle':
                if idle_count>=self.setting('idle_daily_limit',2,0,6) or now-row['last_idle']<self.setting('idle_gap_seconds',14400,3600,86400):return False
                if now-row['last_human']<3600 or now-row['last_human']>86400:return False
                if row['last_human']<=row['last_unsolicited']:return False
                idle_count+=1
            else:
                limit=self.setting('interject_daily_limit',8,-1,10000)
                if limit>=0 and interject_count>=limit:return False
                interject_count+=1
            if not check_only:
                self.db.execute('UPDATE sessions SET day=?,idle_count=?,interject_count=?,last_unsolicited=?,last_idle=? WHERE scope=?',(day,idle_count,interject_count,now,now if mode=='idle' else row['last_idle'],scope))
        return True
