import requests
from esmd_shared.config import ConfigUtility
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from esmd_shared.logger import setup_logger  # Import the shared logger setup function
from typing import Optional, Dict, Any

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
        self.access_token = self.auth_client.get_token()
       

        # # Setup headers
        # self.headers = {
        #     "Authorization": f"Bearer {self.access_token}",
        #     "Content-Type": "application/fhir+json",
        #     "Accept": "application/fhir+json"
        # }


    def get_find_list_trans_notification(self, unique_id: Optional[str] = None,
                                         transaction_status_type: Optional[str] = None,
                                         request_type: Optional[str] = None):
        """Retrieve Esmd-FindListTransactionNotification List resource from the FHIR server."""
        access_token = self.auth_client.get_token()  # Get the token dynamically

        if not access_token:
            self.logger.error("No access token could be retrieved, aborting request.")
            return None

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }

        endpoint = f"{self.fhir_server_url}/List"
        params = {}
        if request_type:
            params["requesttype"] = str(request_type)
        if unique_id:
            params["uniqueid"] = str(unique_id)
        if transaction_status_type:
            params["transaction-status-type"] = str(transaction_status_type)

        response = requests.get(endpoint, headers=headers, params=params, timeout=self.timeout)
        self.logger.info(f"FHIR API response status: {response.status_code}")
        self.logger.info(f"FHIR API response body: {response.text}")
        if response.status_code == 200:
            return response.json(), response.status_code
        else:
            self.logger.error(f"Failed to retrieve notification list: {response.status_code}")
            return response.json(), response.status_code

    def process_notification_list(self, notification_list):
        """Process the retrieved FindListTransNotification List resource."""       
    
        if not notification_list:
            self.logger.warning("No notification list to process.")
            return
         # If payload is a Bundle (searchset)
        if isinstance(notification_list, dict) and notification_list.get("resourceType") == "Bundle":
            for entry in notification_list.get("entry", []):
                try:
                    resource = entry.get("resource", {}) if isinstance(entry, dict) else {}
                    if resource.get("resourceType") == "List":
                       self._process_list(resource)
                    
                except Exception:
                    self.logger.exception("Error processing bundle entry.")
            return

        # If payload is an OperationOutcome at top level
        if isinstance(notification_list, dict) and notification_list.get("resourceType") == "OperationOutcome":
            issues = notification_list.get("issue", [])
            for issue in issues:
                self.logger.warning(f"OperationOutcome issue: {issue.get('diagnostics') or issue.get('details')}")
            return

        self.logger.warning("Notification list did not contain a List/Bundle/OperationOutcome resource.")

    def _process_list(self, list_resource: dict):
        """Extract all meaningful values from a List resource and act on them.

        Returns a list of dicts (one per entry) containing:
          - unique_id
          - status_code
          - transaction_id
          - request_id
          - organization_id
          - review_contractor_oid
          - lines_of_business_id
          - dates (RCCreationDateTime, RCSubmissionDateTime, DeliveryDateTime, RCPickupDateTime)
          - contained (raw contained resource if present)
        """
        if not isinstance(list_resource, dict):
            return []

        # helper to read first value* from extensions with a url suffix
        def _ext_value(resource: dict, suffix: str):
            if not resource:
                return None
            for ext in resource.get("extension", []):
                url = ext.get("url", "")
                if url.endswith(suffix):
                    for k, v in ext.items():
                        if k.startswith("value") and v is not None:
                            return v
            return None

        results = []
        contained_map = {c.get("id"): c for c in list_resource.get("contained", []) if isinstance(c, dict)}

        # list-level extension values (apply to all entries unless overridden by contained)
        list_vals = {
            "transaction_id": _ext_value(list_resource, "Esmd-Ext-TransactionId"),
            "unique_id": _ext_value(list_resource, "Esmd-Ext-UniqueId"),
            "organization_id": _ext_value(list_resource, "Esmd-Ext-OrganizationId"),
            "review_contractor_oid": _ext_value(list_resource, "Esmd-Ext-ReviewContractorOid"),
            "lines_of_business_id": _ext_value(list_resource, "Esmd-Ext-LinesOfBusinessId"),
            "request_id": _ext_value(list_resource, "Esmd-Ext-RequestId"),
            "status_code": _ext_value(list_resource, "Esmd-Ext-StatusCode"),
            "rc_creation_datetime": _ext_value(list_resource, "Esmd-Ext-RCCreationDateTime"),
            "rc_submission_datetime": _ext_value(list_resource, "Esmd-Ext-RCSubmissionDateTime"),
            "delivery_datetime": _ext_value(list_resource, "Esmd-Ext-DeliveryDateTime"),
            "rc_pickup_datetime": _ext_value(list_resource, "Esmd-Ext-RCPickupDateTime"),
        }

        for entry in list_resource.get("entry", []):
            try:
                item = entry.get("item", {}) if isinstance(entry, dict) else {}
                ref = item.get("reference") if isinstance(item, dict) else None

                record = {
                    "unique_id": None,
                    "status_code": None,
                    "transaction_id": list_vals["transaction_id"],
                    "request_id": list_vals["request_id"],
                    "organization_id": list_vals["organization_id"],
                    "review_contractor_oid": list_vals["review_contractor_oid"],
                    "lines_of_business_id": list_vals["lines_of_business_id"],
                    "rc_creation_datetime": list_vals["rc_creation_datetime"],
                    "rc_submission_datetime": list_vals["rc_submission_datetime"],
                    "delivery_datetime": list_vals["delivery_datetime"],
                    "rc_pickup_datetime": list_vals["rc_pickup_datetime"],
                    "contained": None,
                }

                # Resolve reference to contained resource if present (e.g. "#<id>")
                if isinstance(ref, str) and ref.startswith("#"):
                    rid = ref.lstrip("#")
                    contained = contained_map.get(rid)
                    if contained:
                        record["contained"] = contained
                        # contained extensions override list-level values if present
                        record["unique_id"] = record["unique_id"] or _ext_value(contained, "Esmd-Ext-UniqueId") or contained.get("id")
                        record["status_code"] = record["status_code"] or _ext_value(contained, "Esmd-Ext-StatusCode")
                        # if OperationOutcome, capture diagnostics/issues too
                        if contained.get("resourceType") == "OperationOutcome":
                            record["operation_outcome"] = contained.get("issue", [])
                else:
                    # reference may be a dict with identifier
                    if isinstance(ref, dict):
                        identifier = ref.get("identifier")
                        if isinstance(identifier, dict):
                            record["unique_id"] = identifier.get("value")
                    # item.identifier fallback
                    item_identifier = item.get("identifier") if isinstance(item, dict) else None
                    if not record["unique_id"] and isinstance(item_identifier, dict):
                        record["unique_id"] = item_identifier.get("value")

                # final fallbacks to list-level ext values
                record["unique_id"] = record["unique_id"] or list_vals["unique_id"]
                record["status_code"] = record["status_code"] or list_vals["status_code"]

                # normalize strings
                if isinstance(record.get("status_code"), str):
                    record["status_code"] = record["status_code"].strip()
                if isinstance(record.get("unique_id"), str):
                    record["unique_id"] = record["unique_id"].strip()

                results.append(record)
                # call handler so existing behavior remains intact
                if record["unique_id"]:
                    self.logger.info(f"Processing Notification with uniqueId: {record['unique_id']}, statusCode: {record['status_code']}")
                    self.handle_status_code(record["unique_id"], record["status_code"])
                else:
                    self.logger.debug("Could not find unique_id for notification entry; appended empty record.")

            except Exception as e:
                self.logger.exception(f"Error processing list entry: {e}")

        return results

    def handle_status_code(self, unique_id, status_code):
        """Handle specific status codes and take appropriate actions."""
        if status_code == "ready-to-download":
            self.logger.info(f"Initiating download for uniqueId: {unique_id}")
           
            # Implement your download logic here
        elif status_code == "processed":
            self.logger.info(f"File already downloaded for uniqueId: {unique_id}")
           
        else:
            self.logger.info(f"Status {status_code} for uniqueId: {unique_id}")
         

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
    # get_find_list_trans_notification - 3 parameters are optional, pass them as needed
    notification_list = esmd_utility.get_find_list_trans_notification("b75c9847-99ac-47de-9434-f200677b949c", None, None)
    esmd_utility.process_notification_list(notification_list)