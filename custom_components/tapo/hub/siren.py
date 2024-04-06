from math import floor
from typing import Optional
from typing import cast

from homeassistant.components.siren import ATTR_TONE
from homeassistant.components.siren import ATTR_VOLUME_LEVEL
from homeassistant.components.siren import SirenEntity
from homeassistant.components.siren import SirenEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from plugp100.api.requests.set_device_info.play_alarm_params import PlayAlarmParams
from plugp100.new.components.alarm_component import AlarmComponent
from plugp100.new.tapohub import TapoHub

from custom_components.tapo.const import DOMAIN
from custom_components.tapo.coordinators import HassTapoDeviceData, TapoDataCoordinator
from custom_components.tapo.entity import CoordinatedTapoEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    data = cast(HassTapoDeviceData, hass.data[DOMAIN][entry.entry_id])
    if isinstance(data.device, TapoHub):
        if data.coordinator.device.has_alarm:
            available_tones = (
                (await data.device.get_supported_alarm_tones())
                .get_or_raise()
                .tones
            )
            async_add_devices([HubSiren(data.coordinator, data.device, available_tones)], True)


class HubSiren(CoordinatedTapoEntity, SirenEntity):
    _attr_has_entity_name = True
    _attr_supported_features = (
        SirenEntityFeature.TURN_ON
        | SirenEntityFeature.TURN_OFF
        | SirenEntityFeature.VOLUME_SET
        | SirenEntityFeature.TONES
    )

    device: TapoHub

    def __init__(
        self,
        coordinator: TapoDataCoordinator,
        device: TapoHub,
        tones: list[str],
    ) -> None:
        super().__init__(coordinator, device)
        self._attr_available_tones = tones
        self._attr_name = "Siren"

    # @callback
    # def _handle_coordinator_update(self) -> None:
    #     self.async_write_ha_state()

    # @property
    # def unique_id(self):
    #     return self.coordinator.device.device_id
    #
    # @property
    # def name(self):
    #     return "Siren"

    # @property
    # def device_info(self) -> DeviceInfo | None:
    #     return DeviceInfo(
    #         identifiers={(DOMAIN, self.coordinator.device.device_id)}
    #     )

    @property
    def is_on(self) -> Optional[bool]:
        return self.device.is_alarm_on

    async def async_turn_on(self, **kwargs):
        volume = _map_volume_to_discrete_values(
            kwargs.get(ATTR_VOLUME_LEVEL, 1.0), "mute", ["low", "normal", "high"]
        )
        tone = kwargs.get(ATTR_TONE, None)
        play_alarm = PlayAlarmParams(alarm_volume=volume, alarm_type=tone)
        (await self.device.turn_alarm_on(play_alarm)).get_or_raise()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        (await self.device.turn_alarm_off()).get_or_raise()
        await self.coordinator.async_request_refresh()


def _map_volume_to_discrete_values(
    volume: float, mute: str, supported_values: list[str]
) -> str:
    if volume > 0:
        step = 1.0 / (len(supported_values) - 1)
        index = floor(volume / step)
        return supported_values[index]
    else:
        return mute
