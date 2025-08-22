import requests
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from esmd_shared.logger import setup_logger  # Import the shared logger setup function
from esmd_shared.config import ConfigUtility

class BinaryFileExtractor:
    def __init__(self, auth_token=None):
        # Set up the logger for this class using the common logger
        self.logger = setup_logger(self.__class__.__name__)
        # Initialize configuration utility
        self.config_util = ConfigUtility()
        
        # Initialize EsmdAuthClient to get the access token
        self.auth_client = EsmdAuthClient(config_util=self.config_util)

        # Load configurations
        self.fhir_server_url = self.config_util.get_fhir_server_url()
        self.timeout = self.config_util.get_timeout()
        self.access_token = self.config_util.get_auth_token()

        # Setup headers
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/fhir+json"
        }

    def extract_to_file(self, url, output_file_path):
        """
        Extract binary data from the URL and save it to a local file.

        :param url: The URL of the binary document.
        :param output_file_path: The local path where the binary data will be saved.
        :return: True if extraction was successful, False otherwise.
        """
        access_token = self.auth_client.get_token()  # Get the token dynamically

        if not access_token:
            self.logger.error("No access token could be retrieved, aborting request.")
            return None

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/fhir+json"
        }

        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
            headers['Content-Type'] = 'application/fhir+json'
        
        try:
            # Stream the binary data from the URL
            with requests.get(url, stream=True, headers=headers) as response:
                response.raise_for_status()  # Ensure no HTTP errors
                
                # Open the output file in binary write mode and stream data to it
                with open(output_file_path, 'wb') as output_file:
                    for chunk in response.iter_content(chunk_size=8192):  # Stream in chunks of 8KB
                        if chunk:  # Filter out keep-alive new chunks
                            output_file.write(chunk)
                print(f"Document successfully saved to {output_file_path}")
                return True
        
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch binary data from URL: {e}")
            return False
        except Exception as e:
            print(f"An error occurred while saving the file: {e}")
            return False

# Example usage
if __name__ == "__main__":
    # Example configuration
    binary_document_url = "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/Binary/attachment-123"
    output_file_path = "document.pdf"
    auth_token = "your_oauth_token_or_bearer_token"  # Optional token

    # Initialize the extractor
    extractor = BinaryFileExtractor(auth_token=auth_token)

    # Extract and save the binary data to a file
    success = extractor.extract_to_file(binary_document_url, output_file_path)

    if success:
        print("Binary extraction completed successfully.")
    else:
        print("Binary extraction failed.")
