"""Synthetic hand-labelled state-machine demonstration; no SDK/network/model."""
import json
from .core import TopicState


def main():
    state=TopicState(0)
    script=[
        ("alice","Which operator fits this squad?","squad","main",False),
        ("bob","We need another healer","squad","main",False),
        ("carol","I am getting tea","tea","aside",False),
        ("alice","Please recommend tea for me","tea","aside",True),
        ("bob","Back to the squad: use a defender","squad","main",False),
        ("alice","Let us plan dinner","dinner","candidate",False),
        ("bob","Dinner at the noodle place?","dinner","candidate",False),
        ("carol","Yes, noodles at seven","dinner","candidate",False),
        ("alice","I will book the noodle table","dinner","candidate",False),
    ]
    for i,(sender,text,topic,relation,addressed) in enumerate(script):
        mid=str(i); now=i*10
        state.observe(mid,sender,text,now,addressed)
        state.apply(json.dumps({'messages':[{'id':mid,'topic':topic,'relation':relation}]}),[mid],now)
        result=state.context(now,mid if addressed else None)
        print(json.dumps({'step':i+1,'message':text,'main_topic':result['main_topic'],
                          'addressed_id':result['addressed_id'],'metrics':result['metrics'],
                          'retained_ids':[m['id'] for m in result['messages']]},ensure_ascii=False))
    assert state.topic=='dinner'

if __name__=='__main__':main()
