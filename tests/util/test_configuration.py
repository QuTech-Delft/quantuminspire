from unittest.mock import MagicMock

import quantuminspire.util.configuration as configuration


class TestCreate:
    def test_force_file_into_existence_file_does_not_exist(self) -> None:
        path = MagicMock()
        path.exists.return_value = False
        open_mock = MagicMock()
        path.open.return_value = open_mock
        configuration.ensure_config_file_exists(path, "utf-8")
        path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        path.open.assert_called_once_with("w", encoding="utf-8")
        open_mock.write.assert_called_once_with("{}")

    def test_force_file_into_existence_file_exists(self) -> None:
        path = MagicMock()
        path.exists.return_value = True
        open_mock = MagicMock()
        path.open.return_value = open_mock
        configuration.ensure_config_file_exists(path, "utf-8")
        path.parent.mkdir.assert_not_called()
        path.open.assert_not_called()
        path.open().write.assert_not_called()
        open_mock.write.assert_not_called()

    def test_json_config_settings_file_does_not_exist(self) -> None:
        settings = MagicMock()
        settings.Config.env_file_encoding = "utf-8"
        settings.Config.json_config_file = MagicMock()
        settings.Config.json_config_file.exists.return_value = False
        settings.Config.json_config_file.read_text.return_value = "{}"
        assert configuration.json_config_settings(settings) == {}

    def test_json_config_settings_file_does_exist(self) -> None:
        settings = MagicMock()
        settings.Config.env_file_encoding = "utf-8"
        settings.Config.json_config_file = MagicMock()
        settings.Config.json_config_file.exists.return_value = True
        settings.Config.json_config_file.read_text.return_value = '{"auths": "authorisations from file"}'
        assert configuration.json_config_settings(settings) == {"auths": "authorisations from file"}

    def test_customise_sources(self) -> None:
        init_settings = MagicMock()
        env_settings = MagicMock()
        file_secret_settings = MagicMock()
        assert configuration.Settings.Config.customise_sources(init_settings, env_settings, file_secret_settings) == (
            init_settings,
            env_settings,
            configuration.json_config_settings,
            file_secret_settings,
        )

    def test_settings_from_init(self) -> None:
        settings = configuration.Settings(auths={"example.com": {"user_id": "1"}})
        assert settings.auths.items() >= {"example.com": {"user_id": "1"}}.items()
