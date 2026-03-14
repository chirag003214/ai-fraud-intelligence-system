"""
Model loader — singleton pattern for loading MLflow model artifacts.

Supports champion/challenger model registry for A/B testing.
Models are loaded once at startup and held in memory.
"""

from __future__ import annotations

from typing import Any, Literal

import mlflow.pyfunc
import structlog

logger = structlog.get_logger()


class ModelRegistry:
    """
    Holds champion and challenger models in memory.

    Loaded once at startup from local MLflow artifact paths.
    """

    def __init__(self) -> None:
        self._champion: Any = None
        self._challenger: Any = None
        self._champion_version: str = "unknown"
        self._challenger_version: str | None = None

    def load(
        self,
        model_path: str,
        champion_version: str = "latest",
        challenger_path: str | None = None,
        challenger_version: str | None = None,
    ) -> None:
        """Load champion (and optionally challenger) model from disk."""
        logger.info("loading_champion_model", path=model_path, version=champion_version)
        self._champion = mlflow.pyfunc.load_model(model_path)
        self._champion_version = champion_version

        if challenger_path:
            try:
                logger.info("loading_challenger_model", path=challenger_path, version=challenger_version)
                self._challenger = mlflow.pyfunc.load_model(challenger_path)
                self._challenger_version = challenger_version
            except Exception as exc:
                logger.warning("challenger_model_load_failed", error=str(exc))
                self._challenger = None

    def get_variant(self, variant: Literal["champion", "challenger"]) -> Any:
        """Return the model for the specified A/B variant."""
        if variant == "challenger" and self._challenger is not None:
            return self._challenger
        return self._champion

    @property
    def is_loaded(self) -> bool:
        """Check if at least the champion model is loaded."""
        return self._champion is not None

    @property
    def version(self) -> str:
        """Return champion model version string."""
        return self._champion_version


# Module-level singleton
model_registry = ModelRegistry()
