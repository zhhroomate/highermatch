"""
Kafka Consumer
Notification Service
"""

import asyncio
import json
import logging
from typing import Set

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.config import get_settings
from app.services import get_email_service
from app.schemas import (
    MatchCompletedMessage,
    InvoiceGeneratedMessage,
    GuaranteeCreatedMessage,
    ClaimApprovedMessage,
    ClaimRejectedMessage,
)

logger = logging.getLogger(__name__)


class NotificationKafkaConsumer:
    """Kafka consumer for notification events"""

    def __init__(self):
        self.settings = get_settings()
        self.consumer: AIOKafkaConsumer = None
        self.running: bool = False
        self.email_service = get_email_service()

    async def start(self):
        """Start the Kafka consumer"""
        self.consumer = AIOKafkaConsumer(
            self.settings.KAFKA_TOPIC_MATCH_COMPLETED,
            self.settings.KAFKA_TOPIC_INVOICE_GENERATED,
            self.settings.KAFKA_TOPIC_GUARANTEE_CREATED,
            self.settings.KAFKA_TOPIC_CLAIM_APPROVED,
            self.settings.KAFKA_TOPIC_CLAIM_REJECTED,
            bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=self.settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset=self.settings.KAFKA_AUTO_OFFSET_RESET,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        await self.consumer.start()
        self.running = True
        logger.info("Kafka consumer started")

    async def stop(self):
        """Stop the Kafka consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def _process_match_completed(self, message: dict):
        """Process match.completed event"""
        try:
            data = MatchCompletedMessage(**message)
            await self.email_service.send_match_completed(
                employer_email=data.employer_email,
                employer_name=data.employer_name,
                job_id=data.job_id,
                job_title=data.job_title,
                candidate_count=data.candidate_count,
                candidates=[c.model_dump() for c in data.candidates],
                average_match_score=data.average_match_score,
            )
            logger.info(
                f"Sent match notification to {data.employer_email} "
                f"for job {data.job_id}"
            )
        except Exception as e:
            logger.error(f"Failed to process match.completed: {e}")

    async def _process_invoice_generated(self, message: dict):
        """Process invoice.generated event"""
        try:
            data = InvoiceGeneratedMessage(**message)
            await self.email_service.send_invoice_generated(
                employer_email=data.employer_email,
                employer_name=data.employer_name,
                invoice_id=data.invoice_id,
                invoice_no=data.invoice_no,
                invoice_date=data.invoice_date,
                due_date=data.due_date,
                base_fee=data.base_fee,
                urgent_premium=data.urgent_premium,
                total_amount=data.total_amount,
                guarantee_start_date=data.guarantee_start_date,
                guarantee_expiry_date=data.guarantee_expiry_date,
            )
            logger.info(
                f"Sent invoice notification to {data.employer_email} "
                f"for invoice {data.invoice_no}"
            )
        except Exception as e:
            logger.error(f"Failed to process invoice.generated: {e}")

    async def _process_guarantee_created(self, message: dict):
        """Process guarantee.created event"""
        try:
            data = GuaranteeCreatedMessage(**message)
            await self.email_service.send_guarantee_created(
                employer_email=data.employer_email,
                employer_name=data.employer_name,
                guarantee_id=data.guarantee_id,
                guarantee_no=data.guarantee_no,
                start_date=data.start_date,
                expiry_date=data.expiry_date,
            )
            logger.info(
                f"Sent guarantee notification to {data.employer_email} "
                f"for guarantee {data.guarantee_no}"
            )
        except Exception as e:
            logger.error(f"Failed to process guarantee.created: {e}")

    async def _process_claim_approved(self, message: dict):
        """Process claim.approved event"""
        try:
            data = ClaimApprovedMessage(**message)
            await self.email_service.send_claim_approved(
                employer_email=data.employer_email,
                employer_name=data.employer_name,
                claim_id=data.claim_id,
                claim_no=data.claim_no,
                original_candidate_name=data.original_candidate_name,
                leaving_reason=data.leaving_reason,
                review_date=data.review_date,
                replacement_candidate=data.replacement_candidate.model_dump()
                if data.replacement_candidate
                else None,
                estimated_match_date=data.estimated_match_date,
            )
            logger.info(
                f"Sent claim approved notification to {data.employer_email} "
                f"for claim {data.claim_no}"
            )
        except Exception as e:
            logger.error(f"Failed to process claim.approved: {e}")

    async def _process_claim_rejected(self, message: dict):
        """Process claim.rejected event"""
        try:
            data = ClaimRejectedMessage(**message)
            await self.email_service.send_claim_rejected(
                employer_email=data.employer_email,
                employer_name=data.employer_name,
                claim_id=data.claim_id,
                claim_no=data.claim_no,
                guarantee_id=data.guarantee_id,
                original_candidate_name=data.original_candidate_name,
                leaving_reason=data.leaving_reason,
                rejection_reason=data.rejection_reason,
                review_date=data.review_date,
            )
            logger.info(
                f"Sent claim rejected notification to {data.employer_email} "
                f"for claim {data.claim_no}"
            )
        except Exception as e:
            logger.error(f"Failed to process claim.rejected: {e}")

    async def consume(self):
        """Main consume loop"""
        topic_handlers = {
            self.settings.KAFKA_TOPIC_MATCH_COMPLETED: self._process_match_completed,
            self.settings.KAFKA_TOPIC_INVOICE_GENERATED: self._process_invoice_generated,
            self.settings.KAFKA_TOPIC_GUARANTEE_CREATED: self._process_guarantee_created,
            self.settings.KAFKA_TOPIC_CLAIM_APPROVED: self._process_claim_approved,
            self.settings.KAFKA_TOPIC_CLAIM_REJECTED: self._process_claim_rejected,
        }

        logger.info("Starting Kafka consume loop")

        try:
            async for msg in self.consumer:
                if not self.running:
                    break

                topic = msg.topic
                value = msg.value

                logger.debug(f"Received message from {topic}: {value}")

                handler = topic_handlers.get(topic)
                if handler:
                    await handler(value)
                else:
                    logger.warning(f"No handler for topic: {topic}")

        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            raise
        finally:
            await self.stop()

    async def run(self):
        """Run the consumer (start, consume, stop on errors)"""
        await self.start()
        try:
            await self.consume()
        except asyncio.CancelledError:
            logger.info("Consumer cancelled")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            await self.stop()
