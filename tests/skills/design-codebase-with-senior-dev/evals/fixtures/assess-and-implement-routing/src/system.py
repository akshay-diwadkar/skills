def current(value: str) -> str:
    return Wrapper().normalize(value)


class Wrapper:
    def normalize(self, value: str) -> str:
        return value.strip()
