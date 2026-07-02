# -*- coding: utf-8 -*-
"""
Gestion de perfiles de conexion PostgreSQL.
Se guardan en profiles.json dentro del directorio del plugin.
Las contrasenas se almacenan cifradas (XOR + base64).
"""
import json
import os
import base64


def _obfuscate(key, data):
    """XOR simple con clave, luego base64."""
    if not data:
        return ""
    encoded = data.encode("utf-8")
    key_bytes = key.encode("utf-8")
    result = bytearray(len(encoded))
    for i, b in enumerate(encoded):
        result[i] = b ^ key_bytes[i % len(key_bytes)]
    return base64.urlsafe_b64encode(bytes(result)).decode("ascii")


def _deobfuscate(key, data):
    """Base64 luego XOR con clave."""
    if not data:
        return ""
    try:
        decoded = base64.urlsafe_b64decode(data.encode("ascii"))
    except Exception:
        return ""
    key_bytes = key.encode("utf-8")
    result = bytearray(len(decoded))
    for i, b in enumerate(decoded):
        result[i] = b ^ key_bytes[i % len(key_bytes)]
    return result.decode("utf-8")


class ProfileManager:

    CIPHER_KEY = "GeoMigratorPro_S3cur3K3y_2026"

    def __init__(self, plugin_dir):
        self.path = os.path.join(plugin_dir, "profiles.json")
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def names(self):
        return sorted(self._data.keys())

    def get(self, name):
        raw = self._data.get(name, {})
        if not raw:
            return {}
        decrypted = dict(raw)
        if "pwd" in decrypted and decrypted["pwd"]:
            decrypted["pwd"] = _deobfuscate(self.CIPHER_KEY, decrypted["pwd"])
        return decrypted

    def save(self, name, host, port, db, user, pwd, schema, ssl=False):
        self._data[name] = dict(
            host=host, port=port, db=db,
            user=user, pwd=_obfuscate(self.CIPHER_KEY, pwd) if pwd else "",
            schema=schema, ssl=ssl
        )
        self._save()

    def delete(self, name):
        if name in self._data:
            del self._data[name]
            self._save()
