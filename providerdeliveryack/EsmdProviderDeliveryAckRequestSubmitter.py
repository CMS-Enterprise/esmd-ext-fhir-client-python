import requests
import json
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from esmd_shared.logger import setup_logger  # Import the shared logger setup function
from esmd_shared.config import ConfigUtility
from esmd_shared.models import ProviderDeliveryAckMetadata
from providerdeliveryack.ProviderDeliveryAckMetadata import ProviderDeliveryAckMetadataHandler  # Import the shared ProviderDeliveryAckMetadata model

class EsmdProviderDeliveryAckRequestSubmitter:
    def __init__(self):       
        self.logger = setup_logger(self.__class__.__name__)        
        self.config_util = ConfigUtility()   
        self.auth_client = EsmdAuthClient(config_util=self.config_util)
        self.base_url = self.config_util.get_fhir_server_url()

    def submit_provider_delivery_ack(self, fhir_list_resource):
        self.logger.info(f"Submitting Provider Delivery ACK with FHIR LIST resource: {fhir_list_resource}")
        # Implementation for submitting the FHIR LIST resource goes here
        url = f"{self.base_url}/List"
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
            response = requests.post(url, headers=headers, data=json.dumps(fhir_list_resource))
            self.logger.info(f"Received response is: {response.json()}")
            self.logger.info(f"Received response with status code: {response.status_code}")
            return response.json(), response.status_code

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
    

if __name__ == "__main__":
    # Example usage
    metadata = ProviderDeliveryAckMetadata(
        transaction_id="12345",
        organization_id="67890",
        npi="1234567890",
        delivery_datetime="2025-07-08T12:11:20.253-05:00"
    )
    handler = ProviderDeliveryAckMetadataHandler(metadata)
    fhir_list = handler.create_list()
    print(fhir_list)
    submitter = EsmdProviderDeliveryAckRequestSubmitter()
    submitter.submit_provider_delivery_ack(fhir_list)
    print(submitter)