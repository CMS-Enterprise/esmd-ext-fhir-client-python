import json
import requests
from datetime import datetime
from esmd_shared.logger import setup_logger  # Import the shared logger setup function
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from esmd_shared.config import ConfigUtility


class BundleSubmission:
    def __init__(self, esmd_fhir_server_url):
        """
        Initialize the BundleSubmission utility class with the FHIR server URL.
        """
        self.esmd_fhir_server_url = esmd_fhir_server_url
        self.base_url = esmd_fhir_server_url
        # Set up the logger for this class using the common logger
        self.logger = setup_logger(self.__class__.__name__)
        
        # Initialize configuration utility
        self.config_util = ConfigUtility()

        # Initialize EsmdAuthClient to get the access token
        self.auth_client = EsmdAuthClient(config_util=self.config_util)
        self.base_url = self.config_util.get_fhir_server_url()


    def submit_bundle(self, bundle):
        """
        Submit the prepared Bundle to the FHIR server.

        :param bundle: The prepared FHIR Bundle JSON object.
        :return: Response from the FHIR server.
        """
        access_token = self.auth_client.get_token()  # Get the token dynamically
        self.logger.info(f"Retrieved access token successfully , {access_token}")

        
        if not access_token:
            self.logger.error("No access token could be retrieved, aborting request.")
            return None

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/fhir+json',
            'Accept': 'application/fhir+json'
        }
        
        # Ensure the FHIR server URL ends with a '/'
        if not self.esmd_fhir_server_url.endswith('/'):
            self.esmd_fhir_server_url += '/'
        
        try:
            response = requests.post(self.esmd_fhir_server_url, headers=headers, data=json.dumps(bundle))
            response.raise_for_status()
            
            # Log success and return the response
            self.logger.info("Successfully submitted bundle to the FHIR server.")
            
            return True, response.json()  # Return response from server
        except requests.exceptions.HTTPError as http_err:
            self.logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            # Try to parse response.text as JSON, else return as string
            try:
                error_json = json.loads(response.text)
            except Exception:
                error_json = response.text
            return False, {
                "error": str(http_err),
                "status_code": response.status_code,
                "response": error_json
            }

        except requests.exceptions.ConnectionError as conn_err:
            self.logger.error(f"Connection error occurred: {conn_err}")
            return False, {"error": str(conn_err)}

        except requests.exceptions.Timeout as timeout_err:
            self.logger.error(f"Timeout error occurred: {timeout_err}")
            return False, {"error": str(timeout_err)}

        except requests.exceptions.RequestException as req_err:
            self.logger.error(f"Request exception occurred: {req_err}")
            return False, {"error": str(req_err)}

        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            return False, {"error": str(e)}


# Example Usage:
if __name__ == "__main__":

    # Base URL of the FHIR server
    base_url = "https://terminology.esmddev.cms.gov:9012/fhir"
    dir_path = "c:/fhir/testd/"
    # Initialize the generator
    generator = PresignedUrlGenerator(base_url)

    # Example sender OID and file paths
    sender_oid = "2.16.840.1.113883.4.1.1.1234"
    file_paths = [
        "c:/fhir/testd/pkpadmin.pdf",
        "c:/fhir/testd/pkpadmin1.pdf"
    ]

