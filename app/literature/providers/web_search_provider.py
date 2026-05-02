from __future__ import annotations

import logging

from app.core.config import get_settings
from app.literature.providers.base import LiteratureResult


logger = logging.getLogger(__name__)


class GenericWebSearchProvider:
    provider_name = "generic_web"

    def __init__(self) -> None:
        self.settings = get_settings()

    def search(self, query: str, max_results: int = 10) -> list[LiteratureResult]:
        if self.settings.web_search_provider == "none":
            logger.info("Generic web search provider is disabled")
            return []
        logger.warning("Generic web search provider '%s' is configured but not implemented", self.settings.web_search_provider)
        return []
