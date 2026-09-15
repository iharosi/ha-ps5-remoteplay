import pytest
from ps5_remoteplay import Credentials, DeviceInfo, DeviceStatus

from homeassistant.const import CONF_HOST
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ps5_remoteplay.const import CONF_CREDENTIALS, DOMAIN

HOST = "10.12.12.44"
DEVICE_ID = "78C881A62B63"
CREDENTIALS = Credentials(
    account_id="AAAAAAAAAEI=",
    user_credential="305419896",
    registration={"PS5-RegistKey": "3132333435363738", "RP-Key": "00" * 16},
)


def make_device(status: DeviceStatus = DeviceStatus.AWAKE) -> DeviceInfo:
    return DeviceInfo(
        host=HOST,
        id=DEVICE_ID,
        name="PS5-497",
        type="PS5",
        status=status,
        system_version="13600007",
        host_request_port=997,
        data={},
    )


def make_entry(options: dict | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="PS5-497",
        unique_id=DEVICE_ID,
        data={CONF_HOST: HOST, CONF_CREDENTIALS: CREDENTIALS.to_dict()},
        options=options or {},
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
