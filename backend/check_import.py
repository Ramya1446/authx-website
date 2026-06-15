import sys

# Check if local def exists in app.py
with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('=== Checking app.py for local compute_video_fingerprint ===')
found = False
for i, line in enumerate(lines, 1):
    if 'def compute_video_fingerprint' in line:
        print(f'  FOUND at line {i}: {line.strip()}')
        found = True
if not found:
    print('  OK - no local definition found')

print()
print('=== Checking import line ===')
for i, line in enumerate(lines, 1):
    if 'video_fingerprint_patch' in line:
        print(f'  Line {i}: {line.strip()}')

print()
print('=== Testing patch import ===')
try:
    from video_fingerprint_patch import compute_video_fingerprint, compare_video_fingerprints
    import inspect
    print(f'  Loaded from: {inspect.getfile(compute_video_fingerprint)}')
    print('  Import OK')
except Exception as e:
    print(f'  Import FAILED: {e}')

print()
print('=== Testing compare_video_fingerprints ===')
try:
    from video_fingerprint_patch import compare_video_fingerprints
    fp1 = 'a1b2c3d4e5f6a7b8|c9d0e1f2a3b4c5d6|1234567890abcdef'
    fp2 = 'a1b2c3d4e5f6a7b8|c9d0e1f2a3b4c5d6|1234567890abcdef'
    dist = compare_video_fingerprints(fp1, fp2)
    print(f'  Identical fps distance: {dist} (should be 0)')
    fp3 = 'a1b2c3d4e5f6a7b8|c9d0e1f2a3b4c5d6'
    dist2 = compare_video_fingerprints(fp3, fp1)
    print(f'  Partial match distance: {dist2} (should be low <10)')
except Exception as e:
    print(f'  Test FAILED: {e}')

print()
print('=== Testing zero fingerprint detection ===')
try:
    from video_fingerprint_patch import compare_video_fingerprints
    fp_real = 'bc6ecf9f9f94339b|bc6f4f3c9397339b|bc6ccf9f3b93939e|bc6f4f3c9397139b'
    fp_zeros = '0000000000000000|0000000000000000|0000000000000000|0000000000000000'
    dist = compare_video_fingerprints(fp_real, fp_zeros)
    print(f'  Real vs zeros distance: {dist} (will be high - explains the bug)')
except Exception as e:
    print(f'  Test FAILED: {e}')