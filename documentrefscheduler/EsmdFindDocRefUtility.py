from platform import processor
import requests
import json
from esmd_shared.logger import setup_logger
from esmd_shared.config import ConfigUtility
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from .EsmdFhirDocumentReferenceDataProcessor import DocumentReferenceProcessor


class DocumentReferenceRetriever:
    def __init__(self):
        """
        Initialize the DocumentReferenceRetriever with the base FHIR server URL and authorization token.
        """
        # Set up the logger for this class using the common logger
        self.logger = setup_logger(self.__class__.__name__)
        # Initialize configuration utility
        self.config_util = ConfigUtility()
        # Initialize EsmdAuthClient to get the access token
        self.auth_client = EsmdAuthClient(config_util=self.config_util)
        self.base_url = self.config_util.get_fhir_server_url()

    def document_reference_retriever(self, response):
        """
        Process the DocumentReference resources from the FHIR response.
        """
        if not response or 'entry' not in response:
            self.logger.warning("Invalid FHIR response received.")
            return []

        document_references = []
        for entry in response['entry']:
            resource = entry.get('resource')
            if resource and resource['resourceType'] == 'DocumentReference':
                document_references.append(resource)

        self.logger.info(f"Retrieved {len(document_references)} DocumentReference resources.")
        return document_references

    def get_document_reference_bundle(self, transactionid=None, transaction_status_type=None):
        """
        Retrieve a bundle of DocumentReference resources using the provided query parameters.

        :param transactionid: The ID of the transaction (optional).
        :param transaction_status: The transaction status (defaults to 'ready-to-download').
        :return: The bundle of DocumentReference resources or None if there was an error.
        """
     
        try:
            # Get the access token dynamically
            access_token = self.auth_client.get_token()
            if not access_token:
                self.logger.error("No access token could be retrieved, aborting request.")
                return None

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/fhir+json',
                'Accept': 'application/fhir+json'
            }

          # Prepare the query parameters
            query_params = {}
            if transactionid:
                query_params["transactionid"] = str(transactionid)            
            if transaction_status_type:
                query_params["transaction-status-type"] = str(transaction_status_type)
            else:
                query_params["transaction-status-type"] = "ready-to-download"
            # Prepare the query parameters
            self.logger.info(f"Retrieving DocumentReference bundle with query parameters: {query_params}")

            # Construct the request URL with query parameters
            document_reference_endpoint = f"{self.base_url}/DocumentReference"
            self.logger.info(f"Retrieving DocumentReference bundle with transactionid={transactionid} and trans-status={transaction_status_type}")

            # Sending the GET request to retrieve the DocumentReference bundle
            response = requests.get(document_reference_endpoint, headers=headers, params=query_params)

            # Log response status and content
            self.logger.debug(f"Response Status Code: {response.status_code}")
            self.logger.debug(f"Response Content: {response.content}")

            # Check for HTTP errors
            response.raise_for_status()

            # Return the response as JSON (FHIR Bundle)
            self.logger.info("DocumentReference bundle retrieved successfully.")
            return response.json()

        except requests.exceptions.HTTPError as errh:
            self.logger.error(f"HTTP Error occurred: {errh}, Status Code: {response.status_code}, Response: {response.text}")
        except requests.exceptions.ConnectionError as errc:
            self.logger.error(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            self.logger.error(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            self.logger.error(f"Request Error occurred: {err}")
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred: {e}")

        return None

    def get_document_reference(self, transactionid=None, transaction_status_type=None, file_store_location=None):
        """
        Retrieve a single DocumentReference resource by its ID.

        :param document_reference_id: The ID of the DocumentReference resource.
        :return: The DocumentReference resource or None if there was an error.
        """
        
        # Retrieve the document reference bundle
        bundle_response = self.get_document_reference_bundle()

        # Print the bundle response if retrieved successfully
        if bundle_response:
            self.logger.debug(json.dumps(bundle_response, indent=2))
            # Process the bundle using the DocumentReferenceProcessor
            processor = DocumentReferenceProcessor(bundle_response)
            # Extract basic info
            basic_info = processor.extract_basic_info()
            self.logger.info("Basic Info:", basic_info)

            # Extract extensions
            extensions = processor.extract_extensions()
            self.logger.info("Extensions:", extensions)

            # Extract identifiers
            identifiers = processor.extract_identifier()
            self.logger.info("Identifiers:", identifiers)

            # Fetch binary data for all attachments
            all_binary_data = processor.process_and_get_all_binary_data()

            # Optionally, save all binary data to files
            for idx, attachment_data in enumerate(all_binary_data, start=1):
                file_name = f"downloaded_attachment_{idx}.pdf"
                with open(file_name, "wb") as file:
                    file.write(attachment_data['binary_data'])
                self.logger.info(f"Attachment {idx} saved as '{file_name}'.")

        else:
            self.logger.error("Failed to retrieve the DocumentReference bundle.")
        pass

    def process_document_reference_bundle(self, document_reference_bundle):
        """
        Process a single DocumentReference resource.

        :param document_reference: The DocumentReference resource to process.
        """
        if document_reference_bundle and document_reference_bundle.get("resourceType") == "Bundle":
            for entry in document_reference_bundle.get("entry", []):
                resource = entry.get("resource")
                if resource and resource.get("resourceType") == "DocumentReference":
                    processor = DocumentReferenceProcessor(resource)
                    # Extract basic info
                    basic_info = processor.extract_basic_info()
                    self.logger.info(f"Basic Info: {basic_info}")

                # Extract extensions
                    extensions = processor.extract_combined_identifiers_extensions()
                    self.logger.info(f"Extensions: {extensions}")
                    self.logger.info(f"Esmd-Ext-TransactionId: {extensions.get('Esmd-Ext-TransactionId', '')}")
    
                # Fetch binary data for all attachments
                    all_binary_data = processor.process_and_get_all_binary_data(extensions.get('Esmd-Ext-TransactionId', ''))

                # Print the number of binary data entries fetched
                    self.logger.info(f"Fetched {len(all_binary_data)} binary data entries.")
                    self.logger.info(f"Esmd-Ext-TransactionId: {all_binary_data}")
                else:
                    self.logger.warning("No DocumentReference resource found in the bundle entry.")
        elif document_reference_bundle and document_reference_bundle.get("resourceType") == "OperationOutcome":
            self.logger.error(f"OperationOutcome received: {document_reference_bundle}")
            for issue in document_reference_bundle.get("issue", []):
                self.logger.error(f"Issue Severity: {issue.get('severity')}, Code: {issue.get('code')}, Details: {issue.get('details', {}).get('text')}")
        else:
              self.logger.warning("The provided resource is not a Bundle or OperationOutcome.")
# Example usage
if __name__ == "__main__":
    # Example of sender OID
    sender_oid = "1.2.840.10008.3.1.2.1.1"

    # Example of transaction ID
    transaction_id = "12345"

    # Example of transaction status type
    transaction_status_type = "ready-to-download"

    # Example of file store location
    file_store_location = "/path/to/file/store"

    # Create an instance of the utility class
    utility = DocumentReferenceRetriever()

    # Call the method with the example parameters
    document_reference = utility.get_document_reference(transaction_id, transaction_status_type, file_store_location)
