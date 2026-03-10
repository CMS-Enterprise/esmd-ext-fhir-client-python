import requests
from esmd_shared.config import ConfigUtility
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from .EsmdFhirDocumentReferenceDataProcessor import DocumentReferenceProcessor
from apscheduler.schedulers.blocking import BlockingScheduler
from esmd_shared.logger import setup_logger
from notificationscheduler.EsmdFindListTransNotificationUtility import EsmdFindListTransNotificationUtility
from .EsmdFindDocRefUtility import DocumentReferenceRetriever
class TransactionWithPayloadScheduler:
    def __init__(self):
        self.esmd_utility = EsmdFindListTransNotificationUtility()
        self.document_reference_retriever = DocumentReferenceRetriever()
        # Set up the logger for this class using the common logger
        self.logger = setup_logger(self.__class__.__name__)

    def schedule_payloads(self):
        """Fetch notifications and process the list of (uniqueId, status_code) pairs."""
        try:
            # Prepare the list of (uniqueId, status_code) pairs

            self.logger.info("Scheduling with default query parameters with status 'ready-to-download'.")
            self.handle_notification(None, "ready-to-download")           

        except Exception as e:
            self.logger.exception(f"An error occurred while scheduling notifications: {e}")

    def handle_notification(self, transactionid, transaction_status_type):
        """Handle the scheduling logic for each notification."""
        try:
            document_reference_bundle = self.document_reference_retriever.get_document_reference_bundle(transactionid=transactionid, transaction_status_type=transaction_status_type)

            if document_reference_bundle:
                self.logger.info(f"document_reference_bundle: {document_reference_bundle}")
                processor = self.document_reference_retriever.process_document_reference_bundle(document_reference_bundle)
            else:
                self.logger.info(f"No notifications found for uniqueId: {transactionid} and transaction_status_type: {transaction_status_type}")

            # Logic to schedule or process file downloads, etc.
            self.logger.info(f"Scheduling file download for uniqueId: {transactionid}")

        except requests.exceptions.RequestException as req_err:
            self.logger.error(f"Request failed for transactionId: {transactionid} with transaction_status_type: {transaction_status_type}: {req_err}")
        except Exception as e:
            self.logger.exception(f"An error occurred while handling notification for transactionId: {transactionid}: {e}")


def run_scheduler():
    """Setup the scheduler to run the job at regular intervals."""
    try:
        # Set up the scheduler
        scheduler = BlockingScheduler()

        # Create an instance of TransactionWithPayloadScheduler
        document_scheduler = TransactionWithPayloadScheduler()

        # Schedule the job to run every 5 minutes
        scheduler.add_job(document_scheduler.schedule_payloads, 'interval', minutes=1)

        document_scheduler.logger.info("Scheduler started. Jobs will run every 5 minutes.")
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        document_scheduler.logger.info("Scheduler stopped gracefully.")
    except Exception as e:
        document_scheduler.logger.exception(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # Initialize the scheduler
    run_scheduler()
