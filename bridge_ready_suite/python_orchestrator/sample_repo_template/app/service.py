import logging

logger = logging.getLogger(__name__)


def process_name(name: str) -> str:
    logger.info("processing %s", name)
    return f"processing {name}"
