from chromadb import PersistentClient
from collections import Counter

client = PersistentClient(path="/home/nico/.mempalace/palace")
col = client.get_collection("mempalace_drawers")

data = col.get()

rooms = Counter()
types = Counter()
wings = Counter()
hall = Counter()

for meta in data["metadatas"]:
    rooms[meta.get("room")] += 1
    types[meta.get("type")] += 1
    wings[meta.get("wing")] += 1
    hall[meta.get("hall")] += 1

print("=== ROOMS ===")
for k,v in rooms.most_common(10):
    print(k, v)

print("\n=== TYPES ===")
for k,v in types.most_common(10):
    print(k, v)

print("\n=== HALL ===")
for k,v in hall.most_common(10):
    print(k, v)

print("\n=== WINGS ===")
for k,v in wings.most_common(10):
    print(k, v)