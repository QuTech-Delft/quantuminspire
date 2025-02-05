import asyncio

from pytest_mock import MockerFixture

from quantuminspire.util.utils import run_async


async def async_func() -> None:
    await asyncio.sleep(1)


def test_async_run_no_loop() -> None:
    run_async(async_func())


def test_async_run_loop() -> None:
    async def main() -> None:
        run_async(async_func())

    asyncio.run(main())


def test_async_windows(mocker: MockerFixture) -> None:
    mocker.patch("platform.system", return_value="Windows")
    run_async(async_func())

    assert asyncio.get_event_loop_policy() == asyncio.WindowsSelectorEventLoopPolicy()
