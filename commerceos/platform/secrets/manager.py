"""Secret management for CommerceOS.

The SecretManager is deliberately provider-agnostic. It knows only the
SecretProvider contract. Providers may be backed by environment variables,
local files, AWS Secrets Manager, HashiCorp Vault, or any other store.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Sequence
import json
import os

from commerceos.platform.exceptions import CommerceOSError


class SecretProvider(ABC):
    """Abstract provider for secret storage.

    All providers return strings or None. Complex secrets can be stored as JSON strings.
    """

    @abstractmethod
    def get(self, name: str) -> Optional[str]:
        """Retrieve a secret by name. Returns None if not found."""
        raise NotImplementedError

    @abstractmethod
    def set(self, name: str, value: str) -> None:
        """Store a secret by name."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Return True if the secret exists."""
        raise NotImplementedError


class EnvVarProvider(SecretProvider):
    """Provider that reads secrets from environment variables.

    Names are used as-is. Callers may namespace names if desired, e.g.
    ``shopee/2030653/partner_id``.
    """

    def __init__(self, prefix: Optional[str] = None):
        self.prefix = prefix or ""

    def _key(self, name: str) -> str:
        return f"{self.prefix}{name}" if self.prefix else name

    def get(self, name: str) -> Optional[str]:
        return os.environ.get(self._key(name))

    def set(self, name: str, value: str) -> None:
        os.environ[self._key(name)] = value

    def exists(self, name: str) -> bool:
        return self._key(name) in os.environ


class LocalFileProvider(SecretProvider):
    """Provider that stores secrets in a local JSON file.

    This is intentionally a plaintext fallback for local development. It is NOT
    encrypted and must NOT be used for production secrets. Production must use a
    provider backed by a real KMS or secret store.

    The file format is a simple JSON object mapping secret names to secret values.
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path).expanduser().resolve()
        self._secrets: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._secrets = {}
            self._save()
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise SecretProviderError(f"Failed to load secrets from {self.file_path}: {e}")

        if not isinstance(data, dict):
            raise SecretProviderError(f"Secrets file {self.file_path} must contain a JSON object")

        self._secrets = {str(k): str(v) for k, v in data.items()}

    def _save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self._secrets, f, indent=2)

    def get(self, name: str) -> Optional[str]:
        return self._secrets.get(name)

    def set(self, name: str, value: str) -> None:
        self._secrets[name] = value
        self._save()

    def exists(self, name: str) -> bool:
        return name in self._secrets


class SecretManager:
    """Provider-agnostic secret manager.

    The SecretManager interacts with secrets only through the SecretProvider
    interface. It does not know or care whether secrets come from environment
    variables, local files, AWS Secrets Manager, HashiCorp Vault, etc.

    Secret names are free-form strings. Namespacing is a caller convention. For
    example, Shopee store credentials may use
    ``shopee/{store_id}/partner_id``.

    The default provider chain is env var → local file fallback. This can be
    overridden by passing a list of providers.
    """

    def __init__(self, providers: Optional[Sequence[SecretProvider]] = None):
        self.providers: Sequence[SecretProvider] = providers or [
            EnvVarProvider(),
            LocalFileProvider(
                os.environ.get("COMMERCEOS_SECRET_FILE", "~/.commerceos/secrets.json")
            ),
        ]

    def get(self, name: str) -> Optional[str]:
        for provider in self.providers:
            value = provider.get(name)
            if value is not None and value != "":
                return value
        return None

    def get_required(self, name: str) -> str:
        value = self.get(name)
        if value is None or value == "":
            raise SecretNotFoundError(name)
        return value

    def set(self, name: str, value: str, provider_index: int = 0) -> None:
        if not self.providers:
            raise SecretProviderError("No secret providers configured")
        self.providers[provider_index].set(name, value)

    def exists(self, name: str) -> bool:
        return any(provider.exists(name) for provider in self.providers)

    @classmethod
    def from_env(cls, secret_file: Optional[str] = None) -> "SecretManager":
        providers = [EnvVarProvider()]
        if secret_file:
            providers.append(LocalFileProvider(secret_file))
        else:
            providers.append(
                LocalFileProvider(
                    os.environ.get("COMMERCEOS_SECRET_FILE", "~/.commerceos/secrets.json")
                )
            )
        return cls(providers=providers)

    @classmethod
    def default(cls) -> "SecretManager":
        return cls()


class SecretNotFoundError(CommerceOSError):
    """Raised when a required secret is not found."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Secret not found: {name}")


class SecretProviderError(CommerceOSError):
    """Raised when a secret provider fails."""
    pass


# ---------------------------------------------------------------------------
# Workspace-aware helpers
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_ENV_VAR_NAME = "COMMERCEOS_SECRET_FILE"


def workspace_secret_file() -> Path:
    """Return the configured secret file path for this workspace.

    The default is ``<workspace>/.commerceos/secrets.json``. Override with the
    ``COMMERCEOS_SECRET_FILE`` environment variable.
    """
    env_path = os.environ.get(_ENV_VAR_NAME)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return _WORKSPACE_ROOT / ".commerceos" / "secrets.json"


def workspace_secret_manager(secret_file: Optional[Path] = None) -> SecretManager:
    """Return a SecretManager bound to the workspace secret file.

    Environment-variable secrets take precedence, then the workspace secret file.
    """
    path = secret_file or workspace_secret_file()
    return SecretManager.from_env(str(path))


def get_secret_manager() -> SecretManager:
    """Alias for workspace_secret_manager()."""
    return workspace_secret_manager()
