from safecode.guardrail import ShellGuard


ALLOWLIST = [
    "git diff",
    "git status",
    "python -m py_compile",
    "pip install pytest",
    "python -m pip install pytest",
]


def assert_allowed(command: str) -> None:
    assert ShellGuard().check(command, ALLOWLIST) is None


def assert_blocked(command: str) -> None:
    event = ShellGuard().check(command, ALLOWLIST)
    assert event is not None
    assert event.reason == "dangerous_shell_command"


def test_exact_pytest_install_commands_are_allowed() -> None:
    assert_allowed("pip install pytest")
    assert_allowed("python -m pip install pytest")


def test_other_pip_install_commands_are_blocked() -> None:
    assert_blocked("pip install requests")
    assert_blocked("pip install pytest requests")
    assert_blocked("python -m pip install -r requirements.txt")
    assert_blocked("pip install -r requirements.txt")


def test_pytest_install_with_shell_control_suffix_is_blocked() -> None:
    assert_blocked("pip install pytest && rm -rf /")
    assert_blocked("pip install pytest; whoami")
    assert_blocked("python -m pip install pytest && whoami")


def test_existing_prefix_allowlist_commands_still_pass() -> None:
    assert_allowed("git diff")
    assert_allowed("git diff -- src/main.py")
    assert_allowed("git status")
    assert_allowed("python -m py_compile src/main.py")
