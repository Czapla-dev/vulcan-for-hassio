"""The Vulcan component."""
import asyncio
import logging

from aiohttp import ClientConnectorError
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from vulcan import Account, Keystore, Vulcan
from vulcan._utils import VulcanAPIException

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "calendar"]


async def async_setup(hass, config) -> bool:
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass, config_entry):
    try:
        with open(f".vulcan/keystore-{config_entry.data.get('login')}.json") as f:
            keystore = Keystore.load(f)
        with open(f".vulcan/account-{config_entry.data.get('login')}.json") as f:
            account = Account.load(f)
        client = Vulcan(keystore, account)
        await client.select_student()
        students = await client.get_students()
        for student in students:
            if str(student.pupil.id) == str(config_entry.data.get("student_id")):
                client.student = student
                break
    except VulcanAPIException as err:
        if str(err) == "The certificate is not authorized.":
            _LOGGER.error(
                "The certificate is not authorized, please authorize integration again."
            )
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "reauth"},
                )
            )
        else:
            _LOGGER.error("Vulcan API error: %s", err)
        return False
    except FileNotFoundError as err:
        _LOGGER.error(
            "The certificate is not authorized, please authorize integration again."
        )
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "reauth"},
            )
        )
        return False
    except ClientConnectorError as err:
        if "connection_error" not in hass.data[DOMAIN]:
            _LOGGER.error(
                "Connection error - please check your internet connection: %s", err
            )
            hass.data[DOMAIN]["connection_error"] = True
        await client.close()
        raise ConfigEntryNotReady
    num = 0
    for _ in hass.config_entries.async_entries(DOMAIN):
        num += 1
    hass.data[DOMAIN]["students_number"] = num
    hass.data[DOMAIN][config_entry.entry_id] = client

    if not config_entry.update_listeners:
        update_listener = config_entry.add_update_listener(_async_update_options)

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    for platform in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, platform)

    return True


async def _async_update_options(hass, entry):
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


class VulcanEntity(Entity):
    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._state
