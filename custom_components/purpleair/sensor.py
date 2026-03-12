""" The Purple Air air_quality platform. """
import logging

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.sensor import SensorEntity

from .const import DISPATCHER_PURPLE_AIR, DOMAIN, MANUFACTURER, SENSORS_MAP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_schedule_add_entities):
    entities = []
    for index, entity_desc in SENSORS_MAP.items():
        entities.append(PurpleAirQualitySensor(hass, index, config_entry, entity_desc))

    async_schedule_add_entities(entities)


class PurpleAirQualitySensor(SensorEntity):
    """Sensor data reading from purple air device"""
    def __init__(self, hass, index, config_entry, entity_desc):
        self._data = config_entry.data
        self._hass = hass
        self._api = hass.data[DOMAIN]
        self._stop_listening = None

        self._uom = entity_desc.get('uom')
        self._icon = entity_desc.get('icon')
        self._src_key = entity_desc.get('key')
        self._device_class = entity_desc.get('device_class')
        self._entity_category = entity_desc.get('entity_category')

        self.idx = index
        self.pa_sensor_id = self._data['id']
        self.pa_sensor_name = self._data['title']
        self.pa_ip_address = self._data['ip_address']

    @property
    def device_info(self):
        return {
           "configuration_url": f'http://{self.pa_ip_address}',
           "identifiers": {
               # Serial numbers are unique identifiers within a specific domain
               (DOMAIN, self.pa_sensor_id),
               (DOMAIN, self.pa_ip_address)
           },
           "name": f'{self.pa_sensor_name} {MANUFACTURER}',
           "manufacturer": MANUFACTURER,
           "model": f'{self._data["model"]} ({self.pa_ip_address})',
           "sw_version": self._data['sw_version'],
           "hw_version": self._data['hw_version']
        }

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._uom

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class
        
    @property
    def entity_category(self):
        return self._entity_category
    
    @property
    def icon(self):
        return self._icon

    @property
    def name(self):
        nice_entity_title = self.idx.replace('_', ' ').title()
        nice_entity_title = nice_entity_title.replace("Pm1 0", "PM1.0")
        nice_entity_title = nice_entity_title.replace("Pm2 5", "PM2.5")
        nice_entity_title = nice_entity_title.replace("Pm10 0", "PM10")
        nice_entity_title = nice_entity_title.replace("Rh", "RH")
        nice_entity_title = nice_entity_title.replace("Aqi", "AQI")
        nice_entity_title = nice_entity_title.replace("Epa", "EPA")
        nice_entity_title = nice_entity_title.replace("Estimated", "(Estimated)")
        nice_entity_title = nice_entity_title.replace("Operating", "(Operating)")
        
        nice_entity_title = nice_entity_title.replace("PM2.5 Channel A", "PM2.5 Channel (A)")
        nice_entity_title = nice_entity_title.replace("PM2.5 Channel B", "PM2.5 Channel (B)")
        nice_entity_title = nice_entity_title.replace("Pm0 3 Count A", "PM0.3 Count (A)")
        nice_entity_title = nice_entity_title.replace("Pm0 3 Count B", "PM0.3 Count (B)")
        nice_entity_title = nice_entity_title.replace("PM2.5 AQI A", "PM2.5 AQI (A)")
        nice_entity_title = nice_entity_title.replace("PM2.5 AQI B", "PM2.5 AQI (B)")
        
        nice_entity_title = nice_entity_title.replace("PM1.0 Raw", "PM1.0 (Raw)")
        nice_entity_title = nice_entity_title.replace("PM2.5 Raw", "PM2.5 (Raw)")
        nice_entity_title = nice_entity_title.replace("PM10 Raw", "PM10 (Raw)")
        nice_entity_title = nice_entity_title.replace("PM2.5 EPA", "PM2.5 (EPA)")
        nice_entity_title = nice_entity_title.replace("PM2.5 Alt", "PM2.5 (ALT CF=3.4)")
        
        nice_entity_title = nice_entity_title.replace("AQI EPA Raw Pm", "US AQI (Raw PM2.5)")
        nice_entity_title = nice_entity_title.replace("AQI EPA Cor Pm", "US AQI (EPA PM2.5)")
        nice_entity_title = nice_entity_title.replace("AQI EPA Alt Pm", "US AQI (ALT CF=3.4)")
        
        nice_entity_title = nice_entity_title.replace("Voc Iaq Index", "VOC IAQ Index")
        nice_entity_title = nice_entity_title.replace("Voc Iaq Class", "VOC IAQ Class")
        
        nice_entity_title = nice_entity_title.replace("Rssi", "WiFi Signal (RSSI)")
        nice_entity_title = nice_entity_title.replace("Uptime", "Sensor Uptime")
        return f'{self.pa_sensor_name} {nice_entity_title}'

    @property
    def native_value(self):
        value = self._api.get_reading(self.pa_sensor_id, self._src_key)
    
        if not isinstance(value, float):
            return value
    
        # 1 decimal sensors
        if self.idx in {
             "pm1_0_raw",
            "pm2_5_raw",
            "pm2_5_epa",
            "pm2_5_alt",
            "pm10_0_raw",
            "temp_operating",
            "temp_operating_realtime",
            "temp_estimated",
            "rh_operating",
            "rh_operating_realtime",
            "rh_estimated",
            "dewpoint",
            "heat_index",
            "pm0_3_count_a",
            "pm0_3_count_b",
            "pm2_5_channel_a",
            "pm2_5_channel_b",
        }:
            return round(value, 1)
    
        # pressure usually looks better with 2 decimals
        if self.idx == "pressure":
            return round(value, 2)
    
        return value

    @property
    def state_class(self):
        if self.idx == "voc_iaq_index":
            return "measurement"
        return 'measurement' if self._uom is not None else None

    @property
    def unique_id(self):
        return f'{self.pa_sensor_id}_{self.idx}'

    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        return self._api.is_node_registered(self.pa_sensor_id)
    
    async def async_added_to_hass(self):
        self._api.register_node(self.pa_sensor_id, self.pa_ip_address)
        self._stop_listening = async_dispatcher_connect(
            self._hass,
            DISPATCHER_PURPLE_AIR,
            self.async_write_ha_state
        )

    async def async_will_remove_from_hass(self):
        if self._stop_listening:
            self._stop_listening()
            self._stop_listening = None
