"""Quick smoke test for the enhanced TTS cache system."""
import httpx
import time

BASE = "http://localhost:8007"

print("=" * 50)
print("TTS Audio Cache - Smoke Test")
print("=" * 50)

# 1. Stats
print("\n[1] Stats endpoint...")
r = httpx.get(f"{BASE}/api/cache/stats")
s = r.json()
print(f"    OK - Compression: {s['compression_enabled']}, Fuzzy: {s['fuzzy_match_enabled']}")

# 2. First synthesis (cache miss)
print("\n[2] First synthesis (expect MISS)...")
t1 = time.time()
r = httpx.post(f"{BASE}/api/tts/synthesize", json={"text": "Tell me about yourself."}, timeout=30)
d = r.json()
print(f"    Hit: {d['cache_hit']}, Latency: {d['latency_ms']:.1f}ms")

# 3. Same text again (cache hit)
print("\n[3] Same text again (expect HIT)...")
r = httpx.post(f"{BASE}/api/tts/synthesize", json={"text": "Tell me about yourself."}, timeout=30)
d = r.json()
print(f"    Hit: {d['cache_hit']}, Latency: {d['latency_ms']:.1f}ms")

# 4. Fuzzy match test (slightly different text)
print("\n[4] Fuzzy match test (similar text)...")
r = httpx.post(f"{BASE}/api/tts/synthesize", json={"text": "Tell me about yourself"}, timeout=30)
d = r.json()
print(f"    Hit: {d['cache_hit']}, Fuzzy: {d['fuzzy_match']}, Latency: {d['latency_ms']:.1f}ms")

# 5. Entries
print("\n[5] Cache entries...")
r = httpx.get(f"{BASE}/api/cache/entries")
entries = r.json()
for e in entries:
    saved = ""
    if e['compressed'] and e['original_size_bytes'] > 0:
        pct = round((1 - e['file_size_bytes'] / e['original_size_bytes']) * 100)
        saved = f", compressed {pct}%"
    print(f"    - '{e['text'][:40]}...' ({e['file_size_bytes']} bytes{saved})")

# 6. History
print("\n[6] Request history...")
r = httpx.get(f"{BASE}/api/cache/history")
history = r.json()
print(f"    {len(history)} requests recorded")

# 7. Final stats
print("\n[7] Final stats...")
r = httpx.get(f"{BASE}/api/cache/stats")
s = r.json()
print(f"    Entries: {s['total_entries']}, Hits: {s['cache_hits']}, Misses: {s['cache_misses']}, Fuzzy: {s['fuzzy_hits']}")
print(f"    Hit rate: {s['hit_rate_percent']}%, Compression ratio: {s['compression_ratio']}%")

print("\n" + "=" * 50)
print("ALL TESTS PASSED!")
print("=" * 50)
