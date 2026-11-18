"""Read-only local database diagnosis; never prints credentials or candidate text."""
import psycopg
print('Checking isolated PostgreSQL connection...',flush=True)
with psycopg.connect(host='127.0.0.1',port=5433,user='resume',dbname='resume_matcher',connect_timeout=5) as db:
    print('Version:',db.execute('SELECT version()').fetchone(),flush=True)
    print('Tables:',db.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall(),flush=True)
    print('Activity:',db.execute("SELECT pid,state,wait_event_type,wait_event FROM pg_stat_activity WHERE datname=current_database()").fetchall(),flush=True)
