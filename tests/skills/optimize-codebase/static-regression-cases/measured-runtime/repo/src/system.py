def load_users(store):
    return [store.fetch(user_id) for user_id in store.user_ids()]
