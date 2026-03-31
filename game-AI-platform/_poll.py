import urllib.request, json, time

# Create a new game
data = json.dumps({"prompt": "贪吃蛇，复古像素风", "engine": "phaser2d"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/games", data=data,
    headers={"Content-Type": "application/json"},
)
r = urllib.request.urlopen(req)
resp = json.loads(r.read().decode())
pid = resp["id"]
print(f"Created: {pid}")

url = f"http://127.0.0.1:8000/api/v1/games/{pid}"
prev = ""

for i in range(90):
    r = urllib.request.urlopen(url)
    d = json.loads(r.read().decode())
    s = d["status"]
    if s != prev:
        print(f"[{i*10}s] Status: {s}")
        prev = s
    if s in ("ready", "failed"):
        break
    time.sleep(10)

print(f"\nFINAL: {s}")
err = d.get("error", "")
if err:
    print(f"Error: {err[:500]}")
steps = d.get("steps", [])
print(f"Steps: {len(steps)}")
for st in steps:
    name = st.get("name", "?")
    ok = st.get("ok", "?")
    msg = st.get("message", "")[:120]
    dur = st.get("duration_ms", 0)
    print(f"  {name:15s} ok={ok:<5}  {dur:>6}ms  {msg}")
