from app.bootstrap.cli import main
from app.bootstrap.container import build_container
from app.infrastructure.config.settings import Settings
from tests.fakes.fake_model_execution import FakeModelExecution

PROMPT = "PROMPT-MARKER-xyz"


def container_for(fake, **settings):
    return build_container(Settings(_env_file=None, **settings), fake)


def test_cli_success_prints_token_count_and_text(capsys):
    code = main([PROMPT, "--max-new-tokens", "4"], container_for(FakeModelExecution()))
    out = capsys.readouterr().out
    assert code == 0
    assert "prompt_tokens: 1" in out
    assert "fake output" in out


def test_cli_load_failure_returns_1_without_traceback(capsys):
    code = main([PROMPT], container_for(FakeModelExecution(fail_load=True)))
    err = capsys.readouterr().err
    assert code == 1
    assert "Traceback" not in err
    assert PROMPT not in err


def test_cli_unexpected_error_returns_2(capsys):
    class Exploding(FakeModelExecution):
        def generate(self, prompt, config):
            raise RuntimeError(f"boom {prompt}")

    code = main([PROMPT], container_for(Exploding()))
    err = capsys.readouterr().err
    assert code == 2
    assert "Traceback" not in err
    assert PROMPT not in err


def test_cli_rejects_oversized_prompt_with_exit_1(capsys):
    code = main(["x" * 10], container_for(FakeModelExecution(), max_prompt_chars=5))
    assert code == 1
    assert "Traceback" not in capsys.readouterr().err


def test_cli_rejects_max_new_tokens_over_limit(capsys):
    code = main(
        ["hello", "--max-new-tokens", "999"],
        container_for(FakeModelExecution(), max_new_tokens=10),
    )
    assert code == 1
