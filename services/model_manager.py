"""Shared Whisper model loading and switching utilities."""

from __future__ import annotations

import gc
import logging
import threading
from typing import Any


logger = logging.getLogger(__name__)


class ModelManager:
    """Thread-safe cache for Whisper tiny and base models.

    The manager keeps at most one live Whisper model in memory at a time.
    Tiny is cached on first use, base is loaded on demand, and switching
    between them explicitly unloads the inactive model.
    """

    _lock = threading.RLock()
    _tiny_model: Any | None = None
    _base_model: Any | None = None

    _tiny_model_name = "tiny"
    _tiny_download_root = "models/whisper-tiny"
    _base_model_name = "base"
    _base_download_root = "models/whisper"

    @classmethod
    def _load_whisper_model(
        cls,
        model_name_or_path: str,
        download_root: str | None = None,
    ) -> Any:
        """Load a Faster Whisper model using the shared runtime settings."""
        from faster_whisper import WhisperModel

        kwargs: dict[str, Any] = {"device": "cpu", "compute_type": "int8"}
        if download_root is not None:
            kwargs["download_root"] = download_root
        return WhisperModel(model_name_or_path, **kwargs)

    @classmethod
    def _unload_model(cls, model_attr: str) -> None:
        """Drop a cached model reference and force cleanup."""
        setattr(cls, model_attr, None)
        gc.collect()

    @classmethod
    def get_tiny_model(cls, download_root: str | None = None) -> Any:
        """Return the cached tiny Whisper model, loading it on first use."""
        with cls._lock:
            if cls._base_model is not None:
                logger.debug("Unloading base model before loading tiny model.")
                cls._unload_model("_base_model")

            if download_root is not None:
                cls._tiny_download_root = download_root

            if cls._tiny_model is None:
                logger.info("Loading tiny Whisper model.")
                cls._tiny_model = cls._load_whisper_model(
                    cls._tiny_model_name,
                    download_root=cls._tiny_download_root,
                )

            return cls._tiny_model

    @classmethod
    def get_base_model(cls, download_root: str | None = None) -> Any:
        """Load and return the base Whisper model on demand."""
        with cls._lock:
            if cls._tiny_model is not None:
                logger.debug("Unloading tiny model before loading base model.")
                cls._unload_model("_tiny_model")

            if download_root is not None:
                cls._base_download_root = download_root

            if cls._base_model is None:
                logger.info("Loading base Whisper model.")
                cls._base_model = cls._load_whisper_model(
                    cls._base_model_name,
                    download_root=cls._base_download_root,
                )

            return cls._base_model

    @classmethod
    def switch_model(
        cls,
        from_tiny_to_base: bool,
        tiny_download_root: str | None = None,
        base_download_root: str | None = None,
    ) -> Any:
        """Switch the active cached model between tiny and base.

        Args:
            from_tiny_to_base: When True, unload tiny and load base. When False,
                unload base and load tiny.

        Returns:
            The newly active Whisper model.
        """
        with cls._lock:
            if from_tiny_to_base:
                if cls._tiny_model is not None:
                    logger.debug("Switching from tiny to base model.")
                    cls._unload_model("_tiny_model")
                return cls.get_base_model(download_root=base_download_root)

            if cls._base_model is not None:
                logger.debug("Switching from base to tiny model.")
                cls._unload_model("_base_model")
            return cls.get_tiny_model(download_root=tiny_download_root)
