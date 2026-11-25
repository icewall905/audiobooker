"""Tests for audiobooker.conf / environment resolution."""

import configparser

from audiobooker import config as cfg


def write_conf(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_config_paths_prefers_the_env_override(tmp_path, monkeypatch):
    override = tmp_path / "custom.conf"
    monkeypatch.setenv(cfg.ENV_CONF, str(override))
    monkeypatch.chdir(tmp_path)

    paths = cfg.config_paths()

    assert paths[0] == override
    assert paths[1] == tmp_path / "audiobooker.conf"


def test_load_config_reads_the_file(tmp_path):
    conf = write_conf(tmp_path / "audiobooker.conf", "[server]\nurl = http://gpu:9999\n")

    parser = cfg.load_config([conf])

    assert parser.get("server", "url") == "http://gpu:9999"


def test_load_config_ignores_malformed_files(tmp_path):
    broken = write_conf(tmp_path / "broken.conf", "[server\nurl = nope\n")

    parser = cfg.load_config([broken])

    assert not parser.has_section("server")


def test_load_config_skips_missing_files(tmp_path):
    parser = cfg.load_config([tmp_path / "nope.conf"])

    assert parser.sections() == []


def test_server_url_precedence(tmp_path, monkeypatch):
    conf = write_conf(tmp_path / "audiobooker.conf", "[server]\nurl = http://from-conf:7860\n")
    parser = cfg.load_config([conf])

    monkeypatch.delenv(cfg.ENV_SERVER, raising=False)
    assert cfg.resolve_server_url(None, parser) == "http://from-conf:7860"
    assert cfg.resolve_server_url("http://from-flag:1111", parser) == "http://from-flag:1111"

    monkeypatch.setenv(cfg.ENV_SERVER, "http://from-env:2222")
    assert cfg.resolve_server_url(None, parser) == "http://from-env:2222"


def test_server_url_falls_back_to_localhost(monkeypatch):
    monkeypatch.delenv(cfg.ENV_SERVER, raising=False)
    parser = configparser.ConfigParser()

    assert cfg.resolve_server_url(None, parser) == cfg.DEFAULT_SERVER_URL


def test_cli_defaults_coerces_types(tmp_path):
    conf = write_conf(
        tmp_path / "audiobooker.conf",
        "[defaults]\n"
        "max_chunk_length = 120\n"
        "speech_rate = 1.1\n"
        "paragraph_pause = 0\n"
        "split_chapters = true\n"
        "mp3 = no\n"
        "output = book.wav\n",
    )

    values = cfg.cli_defaults(cfg.load_config([conf]))

    assert values == {
        "max_chunk_length": 120,
        "speech_rate": 1.1,
        "paragraph_pause": 0.0,
        "split_chapters": True,
        "mp3": False,
        "output": "book.wav",
    }


def test_cli_defaults_ignores_unknown_and_invalid_keys(tmp_path):
    conf = write_conf(
        tmp_path / "audiobooker.conf",
        "[defaults]\nmax_chunk_length = not-a-number\nunknown_key = 1\nretries = 3\n",
    )

    values = cfg.cli_defaults(cfg.load_config([conf]))

    assert values == {"retries": 3}


def test_cli_defaults_on_a_missing_section(tmp_path):
    conf = write_conf(tmp_path / "audiobooker.conf", "[server]\nurl = http://x:1\n")

    assert cfg.cli_defaults(cfg.load_config([conf])) == {}


def test_env_override_wins_over_cwd_file(tmp_path, monkeypatch):
    write_conf(tmp_path / "audiobooker.conf", "[server]\nurl = http://from-cwd:1\n")
    monkeypatch.chdir(tmp_path)
    override = write_conf(tmp_path / "override.conf", "[server]\nurl = http://override:2\n")
    monkeypatch.setenv(cfg.ENV_CONF, str(override))
    monkeypatch.delenv(cfg.ENV_SERVER, raising=False)

    assert cfg.resolve_server_url() == "http://override:2"
