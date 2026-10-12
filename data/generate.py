"""Generate a fictional, internally consistent NovaPay dataset."""
import json
from pathlib import Path
nodes, edges = [], []
def n(id, type, name, **props):
    nodes.append(dict(id=id,type=type,name=name,updated_at='2026-10-08T10:00:00Z',source='novapay-demo',**props))
def e(a,r,b): edges.append(dict(source=a,type=r,target=b))
for key,name in [('platform','Platform Engineering'),('payments','Payments Engineering'),('data','Data Engineering'),('security','Security'),('product','Product')]: n('team_'+key,'Team',name)
for key,name,title,team in [('david','David Brown','Platform Engineering Lead','platform'),('alice','Alice Johnson','Senior Backend Engineer','payments'),('carol','Carol Williams','Data Engineer','data'),('bob','Bob Smith','Product Manager','product')]:
    n('person_'+key,'Person',name,title=title,availability='AVAILABLE',on_call=key=='david'); e('person_'+key,'MEMBER_OF','team_'+team); e('person_'+key,'LEADS','team_'+team)
for key,name,aliases in [('database','Database Cluster',['postgres','postgresql','database','db']),('gateway','API Gateway',['gateway service','edge gateway','api-gateway']),('payment','Payment Service',['payment infrastructure','payments infrastructure']),('redis','Redis Cache',['redis']),('kafka','Kafka Event Bus',['kafka']),('analytics','Analytics Platform',[]),('auth','Authentication Service',['auth service'])]:
    n('sys_'+key,'System',name,criticality='CRITICAL' if key in ['database','gateway','payment','redis'] else 'HIGH',aliases=aliases,environment='production')
    if key!='redis': e('team_'+('payments' if key=='payment' else 'data' if key in ['analytics','kafka'] else 'platform'),'OWNS','sys_'+key)
for a,b in [('gateway','database'),('payment','gateway'),('payment','database'),('analytics','database'),('analytics','kafka'),('auth','database'),('gateway','redis')]: e('sys_'+a,'DEPENDS_ON','sys_'+b)
for key,name,status in [('payments','Payments v2 Launch','IN_PROGRESS'),('analytics','Analytics Migration','BLOCKED'),('security','Security Compliance Upgrade','IN_PROGRESS'),('mobile','Mobile App Redesign','IN_PROGRESS')]: n('project_'+key,'Project',name,status=status,aliases=['Q4 launch','Payments v2'] if key=='payments' else [])
for a,b in [('payments','payment'),('payments','gateway'),('analytics','analytics'),('security','auth'),('mobile','gateway')]: e('project_'+a,'USES','sys_'+b)
for a,b in [('alice','payments'),('carol','analytics'),('david','security'),('bob','mobile')]: e('person_'+a,'WORKED_ON','project_'+b); e('person_'+a,'OWNS','project_'+b)
for a,b in [('david','database'),('david','gateway'),('alice','payment'),('alice','gateway'),('carol','database'),('carol','analytics')]: e('person_'+a,'WORKED_ON','sys_'+b)
for key,title,text,system,author in [
 ('database','Database Cluster failover runbook','Platform Engineering owns the Database Cluster. David Brown is the on-call lead. Verify replication lag before failover; involve Carol Williams for replication diagnostics.','database','david'),
 ('gateway','API Gateway runbook','Platform Engineering owns API Gateway. David Brown leads incident response. Alice Johnson has routing and payment incident experience.','gateway','alice'),
 ('payments','Payments v2 architecture','Payments v2 Launch uses Payment Service and API Gateway. Payment Service depends on both API Gateway and Database Cluster.','payment','alice'),
 ('analytics','Analytics migration RFC','Analytics Platform depends on Database Cluster and Kafka Event Bus. Migration requires replication lag below the agreed threshold.','analytics','carol')]:
    n('doc_'+key,'Document',title,content=text,url='https://novapay.example/docs/'+key); e('doc_'+key,'ABOUT','sys_'+system); e('person_'+author,'AUTHORED','doc_'+key)
n('ticket_replication','Ticket','DB-212 · Replication lag exceeds threshold',status='OPEN',priority='CRITICAL',content='Replication lag remains above the migration acceptance threshold. Analytics Migration is blocked pending replication validation.',url='https://novapay.example/tickets/DB-212')
e('ticket_replication','BLOCKS','project_analytics'); e('ticket_replication','ABOUT','sys_database'); e('ticket_replication','ASSIGNED_TO','person_carol')
n('ticket_launch','Ticket','PAY-128 · Failover validation',status='IN_PROGRESS',priority='HIGH',content='Payments v2 launch is blocked until database failover validation is complete.',url='https://novapay.example/tickets/PAY-128')
e('ticket_launch','BLOCKS','project_payments'); e('ticket_launch','ABOUT','sys_database'); e('ticket_launch','ASSIGNED_TO','person_alice')
n('incident_114','Incident','INC-114 · Payment request timeouts',status='RESOLVED',content='Database latency propagated through API Gateway and caused payment request timeouts. Alice Johnson resolved the upstream routing configuration issue.',url='https://novapay.example/incidents/114',timestamp='2026-09-21T16:30:00Z')
e('incident_114','AFFECTS','sys_database'); e('incident_114','AFFECTS','sys_gateway'); e('incident_114','RESOLVED_BY','person_alice')
n('message_replication','Message','#data-platform · Migration readiness',content='Carol: Replication validation is incomplete. Keep Analytics Migration paused until DB-212 is resolved.',url='https://novapay.example/chat/migration-readiness',timestamp='2026-10-01T10:30:00Z')
e('message_replication','DISCUSSES','ticket_replication')
n('meeting_planning','Meeting','Engineering migration review',content='Engineering reviewed replication risk and approved delaying Analytics Migration.',timestamp='2026-10-02T09:00:00Z',url='https://novapay.example/meetings/migration-review')
e('meeting_planning','DISCUSSES','project_analytics')
n('decision_delay','Decision','Delay Analytics Migration',rationale='Database replication reliability was not sufficient for migration.',status='APPROVED',created_at='2026-10-02T11:00:00Z')
e('decision_delay','IMPACTS','project_analytics'); e('decision_delay','MADE_BY','person_david')
for key in ['ticket_replication','message_replication','meeting_planning','doc_analytics']: e('decision_delay','BASED_ON',key)
Path(__file__).with_name('sample_company.json').write_text(json.dumps(dict(nodes=nodes,edges=edges),indent=2))
