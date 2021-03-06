"""Preference management for cloud."""
from ipaddress import ip_address

from .const import (
    DOMAIN, PREF_ENABLE_ALEXA, PREF_ENABLE_GOOGLE, PREF_ENABLE_REMOTE,
    PREF_GOOGLE_SECURE_DEVICES_PIN, PREF_CLOUDHOOKS, PREF_CLOUD_USER,
    PREF_GOOGLE_ENTITY_CONFIGS, PREF_OVERRIDE_NAME, PREF_DISABLE_2FA,
    PREF_ALIASES, PREF_SHOULD_EXPOSE,
    InvalidTrustedNetworks)

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
_UNDEF = object()


class CloudPreferences:
    """Handle cloud preferences."""

    def __init__(self, hass):
        """Initialize cloud prefs."""
        self._hass = hass
        self._store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
        self._prefs = None

    async def async_initialize(self):
        """Finish initializing the preferences."""
        prefs = await self._store.async_load()

        if prefs is None:
            prefs = {
                PREF_ENABLE_ALEXA: True,
                PREF_ENABLE_GOOGLE: True,
                PREF_ENABLE_REMOTE: False,
                PREF_GOOGLE_SECURE_DEVICES_PIN: None,
                PREF_GOOGLE_ENTITY_CONFIGS: {},
                PREF_CLOUDHOOKS: {},
                PREF_CLOUD_USER: None,
            }

        self._prefs = prefs

    async def async_update(self, *, google_enabled=_UNDEF,
                           alexa_enabled=_UNDEF, remote_enabled=_UNDEF,
                           google_secure_devices_pin=_UNDEF, cloudhooks=_UNDEF,
                           cloud_user=_UNDEF, google_entity_configs=_UNDEF):
        """Update user preferences."""
        for key, value in (
                (PREF_ENABLE_GOOGLE, google_enabled),
                (PREF_ENABLE_ALEXA, alexa_enabled),
                (PREF_ENABLE_REMOTE, remote_enabled),
                (PREF_GOOGLE_SECURE_DEVICES_PIN, google_secure_devices_pin),
                (PREF_CLOUDHOOKS, cloudhooks),
                (PREF_CLOUD_USER, cloud_user),
                (PREF_GOOGLE_ENTITY_CONFIGS, google_entity_configs),
        ):
            if value is not _UNDEF:
                self._prefs[key] = value

        if remote_enabled is True and self._has_local_trusted_network:
            raise InvalidTrustedNetworks

        await self._store.async_save(self._prefs)

    async def async_update_google_entity_config(
            self, *, entity_id, override_name=_UNDEF, disable_2fa=_UNDEF,
            aliases=_UNDEF, should_expose=_UNDEF):
        """Update config for a Google entity."""
        entities = self.google_entity_configs
        entity = entities.get(entity_id, {})

        changes = {}
        for key, value in (
                (PREF_OVERRIDE_NAME, override_name),
                (PREF_DISABLE_2FA, disable_2fa),
                (PREF_ALIASES, aliases),
                (PREF_SHOULD_EXPOSE, should_expose),
        ):
            if value is not _UNDEF:
                changes[key] = value

        if not changes:
            return

        updated_entity = {
            **entity,
            **changes,
        }

        updated_entities = {
            **entities,
            entity_id: updated_entity,
        }
        await self.async_update(google_entity_configs=updated_entities)

    def as_dict(self):
        """Return dictionary version."""
        return {
            PREF_ENABLE_ALEXA: self.alexa_enabled,
            PREF_ENABLE_GOOGLE: self.google_enabled,
            PREF_ENABLE_REMOTE: self.remote_enabled,
            PREF_GOOGLE_SECURE_DEVICES_PIN: self.google_secure_devices_pin,
            PREF_GOOGLE_ENTITY_CONFIGS: self.google_entity_configs,
            PREF_CLOUDHOOKS: self.cloudhooks,
            PREF_CLOUD_USER: self.cloud_user,
        }

    @property
    def remote_enabled(self):
        """Return if remote is enabled on start."""
        enabled = self._prefs.get(PREF_ENABLE_REMOTE, False)

        if not enabled:
            return False

        if self._has_local_trusted_network:
            return False

        return True

    @property
    def alexa_enabled(self):
        """Return if Alexa is enabled."""
        return self._prefs[PREF_ENABLE_ALEXA]

    @property
    def google_enabled(self):
        """Return if Google is enabled."""
        return self._prefs[PREF_ENABLE_GOOGLE]

    @property
    def google_secure_devices_pin(self):
        """Return if Google is allowed to unlock locks."""
        return self._prefs.get(PREF_GOOGLE_SECURE_DEVICES_PIN)

    @property
    def google_entity_configs(self):
        """Return Google Entity configurations."""
        return self._prefs.get(PREF_GOOGLE_ENTITY_CONFIGS, {})

    @property
    def cloudhooks(self):
        """Return the published cloud webhooks."""
        return self._prefs.get(PREF_CLOUDHOOKS, {})

    @property
    def cloud_user(self) -> str:
        """Return ID from Home Assistant Cloud system user."""
        return self._prefs.get(PREF_CLOUD_USER)

    @property
    def _has_local_trusted_network(self) -> bool:
        """Return if we allow localhost to bypass auth."""
        local4 = ip_address('127.0.0.1')
        local6 = ip_address('::1')

        for prv in self._hass.auth.auth_providers:
            if prv.type != 'trusted_networks':
                continue

            for network in prv.trusted_networks:
                if local4 in network or local6 in network:
                    return True

        return False
