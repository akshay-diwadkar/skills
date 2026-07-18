class current:
    def load(self, user_id: str) -> dict[str, str]:
        raise NotImplementedError


class SqlPreferences(current):
    def load(self, user_id: str) -> dict[str, str]:
        return {"user_id": user_id}


class PreferencesFactory:
    def create(self) -> current:
        return SqlPreferences()


def load_preferences(user_id: str) -> dict[str, str]:
    return PreferencesFactory().create().load(user_id)
