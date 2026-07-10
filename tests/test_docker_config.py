from pathlib import Path


DOCKERFILE = Path("Dockerfile")
DOCKERIGNORE = Path(".dockerignore")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_dockerfile_defines_minimal_task_03_image():
    assert DOCKERFILE.exists(), "Dockerfile must exist"
    content = DOCKERFILE.read_text(encoding="utf-8")

    assert "FROM python:3.10-slim" in content
    assert "useradd" in content and "safecode" in content
    assert "pip install" in content and "-e ." in content
    assert "USER safecode" in content
    assert "EXPOSE 8000" in content
    assert 'CMD ["safecode", "--help"]' in content


def test_dockerignore_excludes_build_noise_and_secrets():
    assert DOCKERIGNORE.exists(), ".dockerignore must exist"
    entries = set(read_lines(DOCKERIGNORE))

    required_entries = {
        ".git",
        "__pycache__/",
        ".venv/",
        ".pytest_cache/",
        ".env*",
        "*.key",
        "*.pem",
    }

    assert required_entries <= entries
