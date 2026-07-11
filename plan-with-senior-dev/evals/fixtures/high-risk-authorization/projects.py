def get_project(tenant_id: str, project_id: str) -> dict[str, str] | None:
    return None


def update_project(actor: dict[str, str], tenant_id: str, project_id: str) -> int:
    project = get_project(tenant_id, project_id)
    if project is None:
        return 404
    if actor["role"] != "admin" or actor["tenant_id"] != tenant_id:
        return 404
    return 204
