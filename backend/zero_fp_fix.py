"""
zero_fp_fix.py - Run this once to diagnose and clean up bad video records.
Copy to backend/ and run: python zero_fp_fix.py
"""
import sqlite3

conn = sqlite3.connect('authx.db')
cursor = conn.cursor()

print('=== Checking all video fingerprints ===')
cursor.execute('SELECT id, content_type, video_fingerprint FROM content_registry WHERE content_type LIKE "video%"')
rows = cursor.fetchall()

bad_ids = []
for r in rows:
    fp = r[2] or ''
    frames = [f for f in fp.split('|') if f]
    all_zeros = all(f == '0' * 16 for f in frames) if frames else True
    has_pipe = '|' in fp
    print(f'  id={r[0]}  has_pipe={has_pipe}  all_zeros={all_zeros}  frame_count={len(frames)}')
    if all_zeros or not has_pipe or len(frames) < 4:
        bad_ids.append(r[0])
        print(f'    --> FLAGGED as bad fingerprint')

print()
if bad_ids:
    print(f'Deleting {len(bad_ids)} bad record(s): ids={bad_ids}')
    cursor.executemany('DELETE FROM content_registry WHERE id = ?', [(i,) for i in bad_ids])
    conn.commit()
    print('Deleted.')
else:
    print('No bad records found.')

print()
print('=== Remaining video records ===')
cursor.execute('SELECT id, content_type, substr(video_fingerprint,1,60) FROM content_registry WHERE content_type LIKE "video%"')
for r in cursor.fetchall():
    print(f'  id={r[0]}  fp={r[2]}')

conn.close()
print()
print('Done. Restart app.py and re-register all videos from scratch.')