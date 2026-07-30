"""Provider-neutral runtime for stateful skill CLIs."""

from .runtime import PROTOCOL_VERSION, validate_manifest

__all__ = ["PROTOCOL_VERSION", "validate_manifest"]
