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


def _metrics_from(stderr: str) -> dict:
    import json

    for line in stderr.splitlines():
        if line.startswith('{"metrics"'):
            return json.loads(line)["metrics"]
    raise AssertionError("no metrics line on stderr")


def test_cli_metrics_go_to_stderr_with_provenance(capsys):
    code = main([PROMPT, "--max-new-tokens", "3", "--metrics"], container_for(FakeModelExecution()))
    captured = capsys.readouterr()
    assert code == 0
    metrics = _metrics_from(captured.err)
    assert metrics["ttft_ms"]["provenance"] == "measured"
    assert metrics["kv_cache_bytes_estimate"]["provenance"] == "derived_from_model_config"
    assert '{"metrics"' not in captured.out


def test_cli_single_token_metrics_show_null_tpot(capsys):
    main([PROMPT, "--max-new-tokens", "1", "--metrics"], container_for(FakeModelExecution()))
    assert _metrics_from(capsys.readouterr().err)["tpot_ms"]["value"] is None


def test_cli_passes_sampling_flags_to_port(capsys):
    fake = FakeModelExecution()
    code = main(
        [
            PROMPT,
            "--temperature",
            "0.8",
            "--top-k",
            "5",
            "--top-p",
            "0.9",
            "--repetition-penalty",
            "1.1",
            "--seed",
            "3",
        ],
        container_for(fake),
    )
    cfg = fake.configs[0]
    assert code == 0
    assert (cfg.temperature, cfg.top_k, cfg.top_p, cfg.repetition_penalty, cfg.seed) == (
        0.8,
        5,
        0.9,
        1.1,
        3,
    )


def test_cli_rejects_invalid_top_p_with_exit_1(capsys):
    code = main(
        [PROMPT, "--temperature", "0.8", "--top-p", "2"], container_for(FakeModelExecution())
    )
    assert code == 1
    assert PROMPT not in capsys.readouterr().err


def test_cli_rejects_greedy_with_top_k_exit_1(capsys):
    code = main([PROMPT, "--top-k", "5"], container_for(FakeModelExecution()))
    assert code == 1
