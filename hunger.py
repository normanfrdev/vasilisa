import json

DATA_FILE = "user_data.json"

def load_data(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data(DATA_FILE)

changed = False
for user_id, user_info in data.items():
    if isinstance(user_info, dict):
        if "hunger" not in user_info:
            user_info["hunger"] = 100
            changed = True
    else:
        # In case user data is not a dict, fix that structure
        data[user_id] = {"items": user_info, "balance": 0, "hunger": 100}
        changed = True

if changed:
    save_data(data, DATA_FILE)
    print("Added hunger to users missing it.")
else:
    print("All users already have hunger.")

