def current(factory):
    client = factory.create()
    return client.request()

