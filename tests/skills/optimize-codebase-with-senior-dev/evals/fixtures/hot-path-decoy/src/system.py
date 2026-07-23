def current(store, identifiers):
    return [store.fetch(identifier) for identifier in identifiers]

