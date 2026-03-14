from __future__ import annotations

import logging


class ProxyTraceLogger:
    def __init__(self) -> None:
        self.logger = logging.getLogger("task_03_proxy.trace")

    def log(self, message: str, **kwargs) -> None:
        self.logger.info("%s | %s", message, kwargs)