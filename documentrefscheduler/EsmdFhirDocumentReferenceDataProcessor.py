import json
import requests
import logging
from urllib.parse import urlparse
from .EsmdBinaryFileExtractor import BinaryFileExtractor

class DocumentReferenceProcessor:
    def __init__(self, document_reference_data):
        try:
            # Parse the JSON data
            self.data = json.loads(document_reference_data)
            self.logger = logging.getLogger(self.__class__.__name__)
            logging.basicConfig(level=logging.INFO)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse document reference data: {e}")
            self.data = None

    def extract_basic_info(self):
        """Extracts basic information from the DocumentReference."""
        if not self.data:
            self.logger.error("No valid data to extract basic info.")
            return {}

        return {
            "resourceType": self.data.get("resourceType", ""),
            "id": self.data.get("id", ""),
            "status": self.data.get("status", ""),
            "date": self.data.get("date", ""),
            "subject_reference": self.data.get("subject", {}).get("reference", "")
        }

    def extract_combined_identifiers_extensions(self):
        """
        Extracts both identifiers and extensions from the DocumentReference and
        combines them into a single dictionary with processed keys and values.
        """
        if not self.data:
            self.logger.error("No valid data to extract identifiers and extensions.")
            return {}

        combined_data = {}

        # Extract identifiers
        identifiers = self.data.get("identifier", [])
        for iden in identifiers:
            system = iden.get("system", "")
            value = iden.get("value", "")
            key = self._get_last_part_from_url(system)
            if key and value:
                combined_data[key] = value
            else:
                self.logger.warning(f"Invalid identifier entry: system={system}, value={value}")

        # Extract extensions
        extensions = self.data.get("extension", [])
        for ext in extensions:
            url = ext.get("url", "")
            value = ext.get("valueString") or ext.get("valueIdentifier", {}).get("value", "")
            key = self._get_last_part_from_url(url)
            if key and value:
                combined_data[key] = value
            else:
                self.logger.warning(f"Invalid extension entry: url={url}, value={value}")

        return combined_data

    def extract_author(self):
        """Extracts authors from the DocumentReference."""
        if not self.data:
            self.logger.error("No valid data to extract authors.")
            return []

        authors = self.data.get("author", [])
        return [{"reference": author.get("reference", "")} for author in authors if author.get("reference")]



    def extract_attachment_info(self):
        """Extracts attachment information from the DocumentReference."""
        if not self.data:
            self.logger.error("No valid data to extract attachment info.")
            return []

        content = self.data.get("content", [])
        attachment_info = []
        for content_item in content:
            attachment = content_item.get("attachment", {})
            if attachment:
                attachment_info.append({
                    "id": attachment.get("id", ""),
                    "contentType": attachment.get("contentType", ""),
                    "language": attachment.get("language", ""),
                    "url": attachment.get("url", ""),
                    "size": attachment.get("size", 0),
                    "hash": attachment.get("hash", ""),
                    "title": attachment.get("title", ""),
                    "creation": attachment.get("creation", "")
                })
            else:
                self.logger.warning("Invalid attachment entry found in content.")
        return attachment_info

    def get_binary_data(self, url, esmd_transaction_id, file_output_location="c:/fhir/data/"):
        """Fetches the binary data from the provided URL."""
        if not url:
            self.logger.error("No URL provided to fetch binary data.")
            return None
        file_extractor = BinaryFileExtractor()
        
        try:
            response = file_extractor.extract_to_file(url, file_output_location)
            
            if response:
              self.logger.info(f"Successfully Extracted and stored file in outputpath.")
              extractor_status = {'esmd_transaction_id': f'{esmd_transaction_id}', 'status': 'success', 'file_url': f'{url}', 'output_file_path': f'{file_output_location}'}
              return extractor_status
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch binary data: {e}")
            return None

    def process_and_get_all_binary_data(self, esmd_transaction_id):
        """Processes the DocumentReference and fetches the binary data for all attachments."""
        # Extract attachment info
        attachments = self.extract_attachment_info()

        if not attachments:
            self.logger.error("No attachments found in the DocumentReference.")
            return []

        all_binary_data = []

        for index, attachment in enumerate(attachments):
            attachment_url = attachment.get("url")

            if not attachment_url:
                self.logger.warning(f"No URL found for attachment {index + 1}. Skipping...")
                continue

            self.logger.info(f"Fetching binary data for attachment {index + 1} from URL: {attachment_url}")
            binary_data = self.get_binary_data(attachment_url, esmd_transaction_id)

            if binary_data:
                self.logger.info(f"Binary data for attachment {index + 1} successfully fetched. Size: {len(binary_data)} bytes.")
                all_binary_data.append(binary_data)

        return all_binary_data

    @staticmethod
    def _get_last_part_from_url(url):
        """Extract the last part of the URL after 'StructureDefinition'."""
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('/')
            return path_parts[-1] if path_parts else ""
        except Exception as e:
            logging.warning(f"Failed to parse URL: {url}. Error: {e}")
            return ""


# Example usage
if __name__ == "__main__":
    # Sample DocumentReference JSON data
    document_reference_data = '''
    {
      "resourceType": "DocumentReference",
      "id": "example-document-reference",
      "meta": {
        "profile": [
          "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/StructureDefinition/Esmd-FindDocumentReference"
        ],
        "security": [
          {
            "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
            "code": "N",
            "display": "normal"
          }
        ]
      },
      "extension": [
        {
          "url": "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/StructureDefinition/Esmd-Ext-LetterId",
          "valueString": "letter-12345"
        },
        {
          "url": "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/StructureDefinition/Esmd-Ext-TransactionId",
          "valueString": "trans-67890"
        }
      ],
      "identifier": [
        {
          "system": "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/StructureDefinition/Esmd-Idn-UniqueId",
          "value": "unique-document-1234"
        }
      ],
      "status": "current",
      "type": {
        "coding": [
          {
            "system": "http://loinc.org",
            "code": "34133-9",
            "display": "Summarization of Episode Note"
          }
        ]
      },
      "subject": {
        "reference": "Patient/example"
      },
      "date": "2024-02-25T16:41:29-06:00",
      "author": [
        {
          "reference": "Practitioner/example"
        }
      ],
      "content": [
        {
          "attachment": {
            "id": "attachment-123",
            "contentType": "application/pdf",
            "language": "en",
            "url": "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/Binary/attachment-123",
            "size": 102400,
            "hash": "SGVsbG8gd29ybGQ=",
            "title": "Medical Document Title",
            "creation": "2024-02-01T08:00:00-06:00"
          }
        },
        {
          "attachment": {
            "id": "attachment-124",
            "contentType": "application/xml",
            "language": "en",
            "url": "http://internal-esmd-dev-apps-986151145.us-east-1.elb.amazonaws.com:8099/fhir/Binary/attachment-124",
            "size": 204800,
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "title": "Sample XML Document",
            "creation": "2024-02-02T08:00:00-06:00"
          }
        }
      ]
    }
    '''

    # Initialize the processor with the sample data
    processor = DocumentReferenceProcessor(document_reference_data)

    # Extract basic info
    basic_info = processor.extract_basic_info()
    print("Basic Info:", basic_info)

    # Extract extensions
    extensions = processor.extract_combined_identifiers_extensions()
    print("Extensions:", extensions)
    print("Esmd-Ext-TransactionId:", extensions.get('Esmd-Ext-TransactionId', ''))
    
    # Fetch binary data for all attachments
    all_binary_data = processor.process_and_get_all_binary_data(extensions.get('Esmd-Ext-TransactionId', ''))

    # Print the number of binary data entries fetched
    print(f"Fetched {len(all_binary_data)} binary data entries.")
    print("Esmd-Ext-TransactionId:", all_binary_data)

    # Optionally, save all binary data to files
    #for idx, attachment_data in enumerate(all_binary_data, start=1):
    #    file_name = f"downloaded_attachment_{idx}.pdf"
    #    with open(file_name, "wb") as file:
    #        file.write(attachment_data['binary_data'])
    #    print(f"Attachment {idx} saved as '{file_name}'.")
