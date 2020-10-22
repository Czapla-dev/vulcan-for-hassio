# This Integration uses unofficial Vulcan-api https://github.com/kapi2289/vulcan-api
import asyncio
from homeassistant import config_entries
import homeassistant
from homeassistant.components import persistent_notification
import json
from vulcan import Vulcan
import voluptuous as vol
import os
import logging
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import (
    CONF_STUDENT_NAME,
    CONF_GROUPS,
    DOMAIN,
    CONF_NOTIFY,
    CONF_ATTENDANCE_NOTIFY,
)


def get_students_list():
    with open("vulcan.json") as f:
        certificate = json.load(f)
    client = Vulcan(certificate)
    for student in client.get_students():
        students_list[str(student.id)] = student.name
    return students_list


_LOGGER = logging.getLogger(__name__)
autherror = False
try:
    if os.stat("vulcan.json").st_size == 0:
        autherror = True
    else:
        with open("vulcan.json") as f:
            certificate = json.load(f)
        client = Vulcan(certificate)
except FileNotFoundError:
    autherror = True


async def async_setup(hass, config) -> bool:
    vulcan: Optional[ConfigType] = config.get(DOMAIN)
    hass.data.setdefault(DOMAIN, {})

    if autherror == True:
        persistent_notification.async_create(
            hass,
            "Coudl not import certificate, try to reconfigure integration",
            "Vulcan: Authentication error",
        )

    if not vulcan:
        return True

    hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)
    return True


async def async_setup_entry(hass, config_entry):
    students_list = get_students_list()
    hass.data[DOMAIN]["notify"] = config_entry.options.get(CONF_NOTIFY)
    hass.data[DOMAIN]["att_notify"] = config_entry.options.get(CONF_ATTENDANCE_NOTIFY)
    try:
        hass.data[DOMAIN]["student_name"] = students_list[
            config_entry.options.get(CONF_STUDENT_NAME)
        ]
    except KeyError:
        hass.data[DOMAIN]["student_name"] = "default"
    for student in client.get_students():
        if student.name == hass.data[DOMAIN]["student_name"]:
            client.set_student(student)
            break
    platform = entity_platform.current_platform.get()
    hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config_entry)
    return True
