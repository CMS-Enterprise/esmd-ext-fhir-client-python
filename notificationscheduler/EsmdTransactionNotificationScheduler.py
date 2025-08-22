import requests
from esmd_shared.config import ConfigUtility
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from .EsmdFindListTransNotificationUtility import EsmdFindListTransNotificationUtility
from apscheduler.schedulers.blocking import BlockingScheduler
from esmd_shared.logger import setup_logger

class NotificationScheduler:
    def __init__(self):
        self.esmd_utility = EsmdFindListTransNotificationUtility()
        # Set up the logger for this class using the common logger
        self.logger = setup_logger(self.__class__.__name__)

    def schedule_notifications(self):
        """Fetch notifications and process the list of (uniqueId, status_code) pairs."""
        try:
            # Prepare the list of (uniqueId, status_code) pairs
            notification_params_metadata = self.esmd_utility.get_find_list_trans_notification_params()

            if notification_params_metadata is None or len(notification_params_metadata) == 0:
                self.logger.info("No notifications found to process.")
                return

            # Process each notification pair
            for notification in notification_params_metadata:
                unique_id = notification.get('unique_id')
                status_code = notification.get('status_code')

                if not unique_id or not status_code:
                    self.logger.warning(f"Invalid notification data: unique_id={unique_id}, status_code={status_code}")
                    continue

                self.logger.info(f"Scheduling notification for uniqueId: {unique_id}, status_code: {status_code}")
                self.handle_notification(unique_id, status_code)

        except Exception as e:
            self.logger.exception(f"An error occurred while scheduling notifications: {e}")

    def handle_notification(self, unique_id, status_code):
        """Handle the scheduling logic for each notification."""
        try:
            notifications_response_list = self.esmd_utility.get_find_list_trans_notification(unique_id=unique_id, status_code=status_code)

            if notifications_response_list:
                self.logger.info(f"Processing notification for uniqueId: {unique_id}")
                self.esmd_utility.process_notification_list(notifications_response_list)
            else:
                self.logger.info(f"No notifications found for uniqueId: {unique_id} and status_code: {status_code}")

            # Logic to schedule or process file downloads, etc.
            self.logger.info(f"Scheduling file download for uniqueId: {unique_id}")

        except requests.exceptions.RequestException as req_err:
            self.logger.error(f"Request failed for uniqueId: {unique_id} with status_code: {status_code}: {req_err}")
        except Exception as e:
            self.logger.exception(f"An error occurred while handling notification for uniqueId: {unique_id}: {e}")


def run_scheduler():
    """Setup the scheduler to run the job at regular intervals."""
    try:
        # Set up the scheduler
        scheduler = BlockingScheduler()

        # Create an instance of NotificationScheduler
        notification_scheduler = NotificationScheduler()

        # Schedule the job to run every 5 minutes
        scheduler.add_job(notification_scheduler.schedule_notifications, 'interval', minutes=5)

        notification_scheduler.logger.info("Scheduler started. Jobs will run every 5 minutes.")
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        notification_scheduler.logger.info("Scheduler stopped gracefully.")
    except Exception as e:
        notification_scheduler.logger.exception(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # Initialize the scheduler
    run_scheduler()
