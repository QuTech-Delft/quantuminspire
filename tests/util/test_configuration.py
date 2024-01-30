from unittest.mock import MagicMock

from pytest_mock import MockerFixture

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
        open_mock.write.assert_called_once_with(
            '{"auths": {"https://staging.qi2.quantum-inspire.com": {"user_id": 1}}}'
        )

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

    def test_json_config_settings_file_does_not_exist(self, mocker: MockerFixture) -> None:
        settings = MagicMock()
        settings.model_config["env_file_encoding"] = "utf-8"
        path_mock = MagicMock()
        mocker.patch("quantuminspire.util.configuration.Path.joinpath", return_value=path_mock)
        path_mock.exists.return_value = False
        path_mock.read_text.return_value = "{}"
        assert configuration.JsonConfigSettingsSource(configuration.Settings)() == {}

    def test_json_config_settings_file_does_exist(self, mocker: MockerFixture) -> None:
        settings = MagicMock()
        settings.model_config["env_file_encoding"] = "utf-8"
        path_mock = MagicMock()
        mocker.patch("quantuminspire.util.configuration.Path.joinpath", return_value=path_mock)
        path_mock.exists.return_value = True
        path_mock.read_text.return_value = '{"auths": "authorisations from file"}'
        assert configuration.JsonConfigSettingsSource(configuration.Settings)() == {"auths": "authorisations from file"}

    def test_json_config_settings_qi2_813(self, mocker: MockerFixture) -> None:
        path_mock = MagicMock()
        mocker.patch("quantuminspire.util.configuration.Path.joinpath", return_value=path_mock)
        path_mock.exists.return_value = True
        path_mock.read_text.return_value = '{"auths": {"host": {"username": "secret_password"}}}'

        settings = configuration.Settings()
        assert settings.auths["host"]["username"] == "secret_password"

    def test_customise_sources(self, mocker: MockerFixture) -> None:
        init_settings = MagicMock()
        env_settings = MagicMock()
        dot_env_settings = MagicMock()
        file_secret_settings = MagicMock()
        json_settings_source = mocker.patch("quantuminspire.util.configuration.JsonConfigSettingsSource")
        assert configuration.Settings.settings_customise_sources(
            configuration.Settings, init_settings, env_settings, dot_env_settings, file_secret_settings
        ) == (
            init_settings,
            env_settings,
            json_settings_source(configuration.Settings),
            file_secret_settings,
        )

    def test_settings_from_init(self) -> None:
        settings = configuration.Settings(auths={"example.com": {"user_id": "1"}})
        assert settings.auths.items() >= {"example.com": {"user_id": "1"}}.items()
