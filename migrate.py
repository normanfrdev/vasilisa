from collections import Counter

def migrate_user_data_to_optimized():
    data = load_user_data()
    changed = False

    for user_id, user_data in data.items():
        items = user_data.get("items", [])
        if isinstance(items, list):
            # convert list -> Counter dict
            item_counts = dict(Counter(items))
            user_data["items"] = item_counts
            changed = True

    if changed:
        save_user_data(data)
        print("Migration to optimized item storage complete.")
    else:
        print("Data already optimized.")
