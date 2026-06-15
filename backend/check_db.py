import sqlite3

conn = sqlite3.connect('authx.db')
cursor = conn.cursor()
cursor.execute('SELECT id, content_type, video_fingerprint FROM content_registry WHERE content_type LIKE "video%"')
rows = cursor.fetchall()
print('Video records:', len(rows))
for r in rows:
    fp = r[2] or ''
    has_pipe = '|' in fp
    print(f'  id={r[0]}')
    print(f'  has pipe separator: {has_pipe}')
    print(f'  first 100 chars: {fp[:100]}')
    print()
conn.close()