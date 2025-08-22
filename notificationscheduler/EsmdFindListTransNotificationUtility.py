import requests
from esmd_shared.config import ConfigUtility
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from esmd_shared.logger import setup_logger  # Import the shared logger setup function


class EsmdFindListTransNotificationUtility:
    def __init__(self):
        # Set up the logger for this class using the common logger
        self.logger = setup_logger(self.__class__.__name__)
        
        # Initialize configuration utility
        self.config_util = ConfigUtility()

        
        # Initialize EsmdAuthClient to get the access token
        self.auth_client = EsmdAuthClient(config_util=self.config_util)

        self.oid = self.config_util.get_oid()
        # Load configurations
        self.fhir_server_url = self.config_util.get_fhir_server_url()
        self.timeout = self.config_util.get_timeout()
        self.access_token = self.config_util.get_auth_token()

        # Setup headers
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/fhir+json"
        }


    def get_find_list_trans_notification(self, unique_id, status_code):
        """Retrieve Esmd-FindListTransactionNotification List resource from the FHIR server."""
        access_token = self.auth_client.get_token()  # Get the token dynamically

        if not access_token:
            self.logger.error("No access token could be retrieved, aborting request.")
            return None

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/fhir+json"
        }



        endpoint = f"{self.fhir_server_url}/List"
        params = {
            "senderOid": f"{self.oid}",
            "uniqueId": f"{unique_id}",
            "trans_status_code": f"{status_code}"
        }
        response = requests.get(endpoint, headers=self.headers, params=params, timeout=self.timeout)

        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Failed to retrieve notification list: {response.status_code}")
            return None

    def process_notification_list(self, notification_list):
        """Process the retrieved FindListTransNotification List resource."""
        if notification_list is not None and 'entry' in notification_list:
            for entry in notification_list['entry']:
                try:
                    list_resource = entry.get('resource', {})

                    if list_resource.get('resourceType') == 'List':
                        for item in list_resource.get('entry', []):
                            document_reference = item.get('item', {}).get('reference', None)
                            if document_reference:
                                unique_id = document_reference.get('identifier', {}).get('value', None)
                                status_code = document_reference.get('status', None)

                                self.logger.info(f"Processing Notification with uniqueId: {unique_id}, statusCode: {status_code}")
                                
                                # You can add further processing logic here
                                self.handle_status_code(unique_id, status_code)

                except Exception as e:
                    self.logger.error(f"Error processing notification entry: {e}")
        else:
            self.logger.warning("No entries found in notification list.")

    def handle_status_code(self, unique_id, status_code):
        """Handle specific status codes and take appropriate actions."""
        if status_code == "file-ready-to-download":
            self.logger.info(f"Initiating download for uniqueId: {unique_id}")
            notification_response = get_find_list_trans_notification(unique_id, status_code)
            # Implement your download logic here
        elif status_code == "file-downloaded":
            self.logger.info(f"File already downloaded for uniqueId: {unique_id}")
            notification_response = get_find_list_trans_notification(unique_id, status_code)
        else:
            self.logger.info(f"Status {status_code} for uniqueId: {unique_id}")
            notification_response = get_find_list_trans_notification(unique_id, status_code)

    def get_find_list_trans_notification_params(self):
        notification_list = [
            {
                'unique_id': 'Test123',
                'status_code': 'ready-for-download'
            },
            {
                'unique_id': 'Test124',
                'status_code': 'ready-for-download'
            }
        ]
        return notification_list
    
# Example usage
if __name__ == "__main__":
    # Initialize the utility class
    esmd_utility = EsmdFindListTransNotificationUtility()

    # Retrieve and process FindListTransNotification
    notification_list = esmd_utility.get_find_list_trans_notification("1234", "ready-for-download")
    esmd_utility.process_notification_list(notification_list)