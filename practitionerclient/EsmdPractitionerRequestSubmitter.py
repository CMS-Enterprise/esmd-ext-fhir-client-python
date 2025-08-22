import requests
import json
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from esmd_shared.logger import setup_logger  # Import the shared logger setup function
from esmd_shared.config import ConfigUtility
from practitionerclient.PractitionerMetadata import PreparePractitionerAndBundlePractitioner  # Import PractitionerMetadata
from practitionerclient.EsmdPractitionerResponse import FhirBatchResponseProcessor
from esmd_shared.models import PractitionerMetadata    # Import the shared PractitionerMetadata model

class PractitionerRequestSubmitter:
    def __init__(self):
        """
        Initialize the PractitionerRequestSubmitter with the base FHIR server URL and authorization token.
        """
        # Set up the logger for this class using the common logger
        self.logger = setup_logger(self.__class__.__name__)
        # Initialize configuration utility
        self.config_util = ConfigUtility()
        # Initialize EsmdAuthClient to get the access token
        self.auth_client = EsmdAuthClient(config_util=self.config_util)
        self.base_url = self.config_util.get_fhir_server_url()

    def submit_practitioner(self, practitioner_json):
        """
        Submit the Practitioner resource to the FHIR server.

        :param practitioner_json: JSON body of the Practitioner resource (Esmd-Practitioner).
        :return: Response object from the FHIR server or None in case of an error.
        """
        if not practitioner_json:
            self.logger.error("Empty practitioner JSON provided, aborting submission.")
            return None

        try:
            access_token = self.auth_client.get_token()  # Get the token dynamically
            if not access_token:
                self.logger.error("No access token could be retrieved, aborting request.")
                return None

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/fhir+json',
                'Accept': 'application/fhir+json'
            }

           
            # Endpoint for Practitioner resource
            practitioner_endpoint = f'{self.base_url}/Practitioner/{practitioner_json['id']}'

            self.logger.info(f"Submitting Practitioner resource to {practitioner_endpoint}")

            # Sending the request to the FHIR server
            response = requests.put(practitioner_endpoint, headers=headers, data=json.dumps(practitioner_json))
            
            # Log response status and content
            self.logger.debug(f"Response Status Code: {response.status_code}")
            self.logger.debug(f"Response Content: {response.content}")

            # Raise an exception for HTTP errors
            response.raise_for_status()

            self.logger.info("Practitioner resource submitted successfully.")
            return response.json()  # Return the response as JSON

        except requests.exceptions.HTTPError as errh:
            if response.status_code == 400:
                self.logger.error(f"400 Bad Request: {response.text}")
            else:
                self.logger.error(f"HTTP Error occurred: {errh}, Status Code: {response.status_code}, Response: {response.text}")
        except requests.exceptions.ConnectionError as errc:
            self.logger.error(f"Error Connecting: {errc} ")
        except requests.exceptions.Timeout as errt:
            self.logger.error(f"Timeout Error: {errt} ")
        except requests.exceptions.RequestException as err:
            self.logger.error(f"Request Error occurred: {err} ")
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred: {e}")

        return None

    def submit_practitioner_bundle(self, bundle_practitioners_json):
        """
        Submit a list of Practitioner resources to the esMD FHIR server in a batch.

        :param bundle_practitioners_json: JSON body of the Practitioner Bundle resource.
        :return: Response object from the FHIR server or None in case of an error.
        """
        if not bundle_practitioners_json:
            self.logger.error("Empty practitioner bundle JSON provided, aborting submission.")
            return None

        try:
            access_token = self.auth_client.get_token()  # Get the token dynamically
            if not access_token:
                self.logger.error("No access token could be retrieved, aborting request.")
                return None

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/fhir+json',
                'Accept': 'application/fhir+json'
            }

            # Endpoint for Bundle resource
            bundle_endpoint = f'{self.base_url}'

            self.logger.info(f"Submitting Practitioner Bundle resource to {bundle_endpoint}")

            # Sending the request to the FHIR server
            response = requests.post(bundle_endpoint, headers=headers, data=json.dumps(bundle_practitioners_json))
            
            # Log response status and content
            self.logger.debug(f"Response Status Code: {response.status_code}")
            self.logger.debug(f"Response Content: {response.content}")

            # Raise an exception for HTTP errors
            response.raise_for_status()

            self.logger.info("Practitioner Bundle resource submitted successfully.")
            return response.json()  # Return the response as JSON

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


# Example usage
if __name__ == "__main__":
    # Initialize the PractitionerRequestSubmitter
    submitter = PractitionerRequestSubmitter()

    practitioner1_dc = PractitionerMetadata(
        family_name="Doe",
        given_name=["John"],
        gender="male",
        npi="1234567890",
        provider_number="5432112345",
        provider_taxid="TAXID123",
        action_requested="A",
        service_code="EEP",
        service_start_date="2024-01-01",
        service_end_date="2024-01-31",
        address=[{
            "line": ["123 Main St"],
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62701",
            "country": "USA"
        }],
        telecom=[{
            "system": "phone",
            "value": "555-123-4567",
            "use": "work"
        }]
    )

    practitioner2_dc = PractitionerMetadata(
        family_name="Smith",
        given_name=["Jane"],
        gender="female",
        npi="9876543210",
        provider_number="5432112345",
        provider_taxid="TAXID987",
        action_requested="A",
        service_code="EEP",
        service_start_date="2024-02-01",
        service_end_date="2024-02-28",
        address=[{
            "line": ["456 Oak Ave"],
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62702",
            "country": "USA"
        }],
        telecom=[{
            "system": "phone",
            "value": "555-987-6543",
            "use": "work"
        }]
    )

    # Use PreparePractitionerAndBundlePractitioner to create resources
    prep1 = PreparePractitionerAndBundlePractitioner(practitioner1_dc)
    prep2 = PreparePractitionerAndBundlePractitioner(practitioner2_dc)

    practitioner_metadata_1 = prep1.create_practitioner()
    practitioner_metadata_2 = prep2.create_practitioner()

    practitioners_metadata_list = [practitioner_metadata_1, practitioner_metadata_2]

    # # Create Bundle Practitioner resource
    # bundle_practitioner = PreparePractitionerAndBundlePractitioner.create_practitioner_bundle(practitioners_metadata_list)

    # # Submit the practitioner bundle
    # print("Submitting Practitioner Bundle...")
    # bundle_response = submitter.submit_practitioner_bundle(bundle_practitioner)

    # # Print the response
    # if bundle_response:
    #     print("Practitioner Bundle Submission Response:")
    #     print(json.dumps(bundle_response, indent=2))
    #     processor = FhirBatchResponseProcessor(bundle_response)
    #     practitioner_response_list = processor.extract_practitioner_ids_with_status()
    #     # Print the extracted practitioner information
    #     print("Extracted Practitioner Information:", json.dumps(practitioner_response_list, indent=2))
    # else:
    #     print("Failed to submit the practitioner bundle.")

    
    # Test Practitioner Resource Functionality
    print("Testing Practitioner Resource Functionality...")
    for practitioner in practitioners_metadata_list:
        print(f"Testing Practitioner: {practitioner['id']}")
        # Submit the practitioner bundle
        print("Submitting Practitioner Bundle...")
        practitioner_response = submitter.submit_practitioner(practitioner)
        if practitioner_response:
            print("Practitioner Submission Response:")
        else:
            print("Failed to submit the practitioner.")
