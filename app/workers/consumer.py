import asyncio
import logging
import uuid

from faststream import AckPolicy, FastStream
from faststream.rabbit import Channel
from pydantic import BaseModel

from app.core.broker import broker, dead_letter_queue, process_queue
from app.core.logging import log_context, setup_logging

logger = logging.getLogger(__name__)

app = FastStream(broker)


class DocumentTask(BaseModel):
    document_id: uuid.UUID


@broker.subscriber(
    process_queue,
    channel=Channel(prefetch_count=1),
    ack_policy=AckPolicy.REJECT_ON_ERROR,
)
async def process_document(task: DocumentTask) -> None:
    with log_context(document_id=str(task.document_id)):
        logger.info("document task received")


@app.after_startup
async def declare_dead_letter_queue() -> None:
    await broker.declare_queue(dead_letter_queue)


def main() -> None:
    setup_logging()
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
