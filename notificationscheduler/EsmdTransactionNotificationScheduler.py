from flask import json
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

    def schedule_notifications(self, notification_params_metadata=None):
        """Fetch notifications and process the list of (uniqueId, status_code) pairs."""
        try:
            # Prepare the list of (uniqueId, status_code) pairs
            #notification_params_metadata = self.esmd_utility.get_find_list_trans_notification_params()

            params = notification_params_metadata
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except Exception:
                    # leave as-is (will be treated invalid below)
                    pass

            if isinstance(params, dict):
                params = [params]

            if params is None or (isinstance(params, (list, tuple)) and len(params) == 0):
                self.logger.info("No parameters found. Scheduling default notification with status 'ready-to-download'.")
                self.handle_notification(None, "ready-to-download", None)
                return

            def _norm(v):
                if v is None:
                    return None
                if isinstance(v, str):
                    s = v.strip()
                    return s if s else None
                return v

            for notification in params:
                n = notification or {}
                # accept multiple key variants
                unique_id = _norm(n.get("uniqueid") or n.get("unique_id"))
                transaction_status_type = _norm(
                    n.get("transaction-status-type")
                    or n.get("transaction_status_type")                    
                )
                requesttype = _norm(n.get("requesttype") or n.get("request_type") or n.get("requestType"))
                self.logger.info(f"Scheduling notification for uniqueId: {unique_id}, transaction_status_type: {transaction_status_type}")
            self.handle_notification(unique_id, transaction_status_type, requesttype)

           

        except Exception as e:
            self.logger.exception(f"An error occurred while scheduling notifications: {e}")

    def handle_notification(self, unique_id=None, transaction_status_type=None, request_type=None):
        """Handle the scheduling logic for each notification."""
        try:
            notifications_response_list, http_status_code = self.esmd_utility.get_find_list_trans_notification(unique_id=unique_id, transaction_status_type=transaction_status_type, request_type=request_type)

            if http_status_code == 200 and notifications_response_list:
                self.logger.info(f"Processing notification for uniqueId: {unique_id}")
                self.esmd_utility.process_notification_list(notifications_response_list)            
            else:
                if notifications_response_list and notifications_response_list.get("resourceType") == "OperationOutcome":
                    # If the response is an OperationOutcome, log issues and exit
                    issues = notifications_response_list.get("issue", [])
                    for issue in issues:
                        self.logger.warning(f"OperationOutcome issue: {issue.get('diagnostics') or issue.get('details')}")
                    return           


        except requests.exceptions.RequestException as req_err:
            self.logger.error(f"Request failed for uniqueId: {unique_id} with http_status_code: {http_status_code}: {req_err}")
        except Exception as e:
            self.logger.exception(f"An error occurred while handling notification for uniqueId: {unique_id}: {e}")


def run_scheduler(params: dict | None = None):
    """Setup the scheduler to run the job at regular intervals."""
    try:
        # Set up the scheduler
        scheduler = BlockingScheduler()

        # Create an instance of NotificationScheduler
        notification_scheduler = NotificationScheduler()
        # If provided, set scheduler.params so handler can access them
        if params:
            notification_scheduler.params = params
        # Schedule the job to run every 5 minutes
        scheduler.add_job(notification_scheduler.schedule_notifications, 'interval', minutes=1)

        notification_scheduler.logger.info("Scheduler started. Jobs will run every 5 minutes.")
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        notification_scheduler.logger.info("Scheduler stopped gracefully.")
    except Exception as e:
        notification_scheduler.logger.exception(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # Initialize the scheduler  
    # Run the scheduler with optional parameters or the default behavior 
    # By default, it will pull all notifications with status 'ready-to-download'
    # if you want to pass specific parameters like requesttype parameter or uniqueid, you can do so like this and call run_scheduler with a dict
    run_scheduler({"uniqueid": "b75c9847-99ac-47de-9434-f200677b949c"})
    #notification_scheduler = NotificationScheduler()
    #notification_scheduler.schedule_notifications({"uniqueid": "b75c9847-99ac-47de-9434-f200677b949c"})
