from real_estate.infrastructure.config.settings import Environment, Settings


def test_settings_default_environment_is_dev() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment is Environment.DEV
    assert settings.log_level == "INFO"


def test_settings_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.PROD
    assert settings.log_level == "WARNING"
