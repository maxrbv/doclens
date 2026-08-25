import logging
import uuid
from types import TracebackType

from faststream import BaseMiddleware
from faststream.rabbit import RabbitBroker, RabbitQueue

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LogFailureMiddleware(BaseMiddleware):
    async def after_processed(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> bool | None:
        if exc_type is not None:
            logger.error(
                "message rejected to dead letter queue",
                exc_info=(exc_type, exc_val, exc_tb),
            )
        return await super().after_processed(exc_type, exc_val, exc_tb)


PROCESS_QUEUE_NAME = "documents.process"
DLQ_NAME = "documents.process.dlq"

dead_letter_queue = RabbitQueue(DLQ_NAME, durable=True)

process_queue = RabbitQueue(
    PROCESS_QUEUE_NAME,
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": DLQ_NAME,
    },
)

broker = RabbitBroker(
    get_settings().rabbitmq_url,
    logger=None,
    middlewares=(LogFailureMiddleware,),
)


async def publish_document_task(document_id: uuid.UUID) -> None:
    await broker.publish(message={"document_id": str(document_id)}, queue=process_queue)
