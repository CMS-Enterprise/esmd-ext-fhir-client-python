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

    def get_document_reference_bundle(self, sender_oid, transaction_status='ready-for-download'):
        """
        Retrieve a bundle of DocumentReference resources using the provided query parameters.

        :param sender_oid: The OID of the sender (required).
        :param transaction_status: The transaction status (defaults to 'ready-for-download').
        :return: The bundle of DocumentReference resources or None if there was an error.
        """
        if not sender_oid:
            self.logger.error("Sender OID is required but not provided.")
            return None

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
            query_params = {
                'senderOid': sender_oid,
                'trans-status': transaction_status
            }

            # Construct the request URL with query parameters
            document_reference_endpoint = f"{self.base_url}/DocumentReference"
            self.logger.info(f"Retrieving DocumentReference bundle with senderOid={sender_oid} and trans-status={transaction_status}")

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
    
    def get_document_reference(self, sender_oid, file_store_location):
        """
        Retrieve a single DocumentReference resource by its ID.

        :param document_reference_id: The ID of the DocumentReference resource.
        :return: The DocumentReference resource or None if there was an error.
        """
        
        # Retrieve the document reference bundle
        bundle_response = self.get_document_reference_bundle(sender_oid)

        # Print the bundle response if retrieved successfully
        if bundle_response:
            self.logger.debug(json.dumps(bundle_response, indent=2))
            # Process the bundle using the DocumentReferenceProcessor
            processor = DocumentReferenceProcessor(bundle_response)
            # Extract basic info
            basic_info = processor.extract_basic_info()
            print("Basic Info:", basic_info)

            # Extract extensions
            extensions = processor.extract_extensions()
            print("Extensions:", extensions)

            # Extract identifiers
            identifiers = processor.extract_identifier()
            print("Identifiers:", identifiers)

            # Fetch binary data for all attachments
            all_binary_data = processor.process_and_get_all_binary_data()

            # Optionally, save all binary data to files
            for idx, attachment_data in enumerate(all_binary_data, start=1):
                file_name = f"downloaded_attachment_{idx}.pdf"
                with open(file_name, "wb") as file:
                    file.write(attachment_data['binary_data'])
                print(f"Attachment {idx} saved as '{file_name}'.")
            
        else:
            print("Failed to retrieve the DocumentReference bundle.")
        pass
    



# Example usage
if __name__ == "__main__":
    # Example of sender OID
    sender_oid = "1.2.840.10008.3.1.2.1.1"

    
