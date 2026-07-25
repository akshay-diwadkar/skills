"""Pytest fixtures for build-codebase-knowledge unit tests."""

import pytest
import shutil
import subprocess
from pathlib import Path

@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()

    # Create structure
    src_auth = repo_dir / "src" / "auth"
    src_auth.mkdir(parents=True)
    (src_auth / "__init__.py").write_text("", encoding="utf-8")
    (src_auth / "service.py").write_text(
        "class AuthService:\n"
        "    def authenticate(self, username, password):\n"
        "        return True\n\n"
        "    def reset_password(self, email):\n"
        "        return True\n",
        encoding="utf-8"
    )

    src_api = repo_dir / "src" / "api"
    src_api.mkdir(parents=True)
    (src_api / "main.py").write_text(
        "from src.auth.service import AuthService\n\n"
        "def create_app():\n"
        "    auth = AuthService()\n"
        "    return auth\n\n"
        "if __name__ == '__main__':\n"
        "    create_app()\n",
        encoding="utf-8"
    )

    tests_dir = repo_dir / "tests" / "auth"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_service.py").write_text(
        "from src.auth.service import AuthService\n\n"
        "def test_authenticate():\n"
        "    auth = AuthService()\n"
        "    assert auth.authenticate('user', 'pass')\n",
        encoding="utf-8"
    )

    config_dir = repo_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "rate_limits.yaml").write_text(
        "rate_limits:\n  password_reset: 5\n", encoding="utf-8"
    )
    (repo_dir / ".env.example").write_text(
        "DATABASE_URL=postgres://user:pass@localhost/db\n", encoding="utf-8"
    )

    # Vendor directory (to test exclusion)
    vendor_dir = repo_dir / "vendor"
    vendor_dir.mkdir()
    (vendor_dir / "lib.py").write_text("# vendored code\n", encoding="utf-8")

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=False)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, capture_output=True, check=False)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, capture_output=True, check=False)
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=False)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True, check=False)

    return repo_dir
