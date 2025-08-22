import requests
import os
from esmd_shared.logger import setup_logger  # Import the shared logger setup function
from esmd_shared.auth import EsmdAuthClient  # Import the shared EsmdAuthClient class
from esmd_shared.config import ConfigUtility

class PresignedUrlUploader:
    def __init__(self):
        """
        Initialize the PresignedUrlUploader utility class.
        """
        
        
        # Initialize configuration utility
        self.config_util = ConfigUtility()

        # Set up the logger for this class using the common logger
        self.logger = setup_logger(self.__class__.__name__)

        # Initialize EsmdAuthClient to get the access token
        self.auth_client = EsmdAuthClient(config_util=self.config_util)
        self.base_url = self.config_util.get_fhir_server_url()

    def upload_file(self, presigned_url, file_path, md5str, content_length, content_type='application/octet-stream'):
        """
        Uploads a file to a pre-signed URL using a PUT request.

        :param presigned_url: The pre-signed URL to which the file will be uploaded.
        :param file_path: The local path to the file to be uploaded.
        :param content_type: The content type of the file being uploaded (default is 'application/octet-stream').
        :return: Response from the server or None in case of error.
        """
        try:
            # Verify if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            access_token = self.auth_client.get_token()  # Get the token dynamically

            if not access_token:
                self.logger.error("No access token could be retrieved, aborting request.")
                return None
            
            # Open the file in binary mode for uploading
            with open(file_path, 'rb') as file_data:

                # Perform the PUT request to upload the file
                headers = {
                    'Content-Type': f'{content_type}',
                    'Authorization': f'Bearer {access_token}',
                    'content-md5': f'{md5str}',
                    'content-length': f'{content_length}'
                }
                response = requests.post(presigned_url, headers=headers, data=file_data )

                # Check for successful upload (status code 200-299)
                if 200 <= response.status_code < 300:
                    print(f"File {file_path} successfully uploaded.")
                else:
                    print(f"Failed to upload file. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                
                return response.text
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error during the upload request: {e}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

# Example Usage
if __name__ == "__main__":
    uploader = PresignedUrlUploader()

    # Example pre-signed URL and file path
    presigned_url = "https://your-bucket.s3.amazonaws.com/your-file.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=..."
    file_path = "tests/sample_files/realtimepayload1.xml"

    content_md5 = "example_md5_hash"  # Replace with actual MD5 hash if needed
    content_length = os.path.getsize(file_path)

    # Upload the file
    response = uploader.upload_file(presigned_url, file_path, content_md5, content_length, content_type='application/xml')

    # Print response if available
    if response:
        print("Response headers:", response.headers)
