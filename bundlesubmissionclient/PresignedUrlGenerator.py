"""
Enhanced PresignedUrlGenerator for EsmdFHIRClient.

This module provides improved presigned URL generation with comprehensive
validation, error handling, retry logic, and type safety.
"""

import json
import os
import string
import random
from typing import Optional, Dict, Any, List, Tuple, Union
from pathlib import Path

import requests


from esmd_shared.auth import EsmdAuthClient
from esmd_shared.config import ConfigUtility  
from esmd_shared.logger import setup_logger
from esmd_shared.models import (
    LoggerConfig, PresignedUrlRequest, PresignedUrlResponse, FileUploadInfo,
    HTTPRequest, HTTPResponse, ValidationResult, RetryConfig
)
from esmd_shared.exceptions import (
    PresignedUrlError, RetryExhaustedError, ValidationError, FileOperationError,
    AuthenticationError, NetworkError
)
from esmd_shared.utils import (
    validate_required_fields, validate_file_path, calculate_file_md5,
    get_content_type, retry_with_backoff, sanitize_filename
)
from bundlesubmissionclient.PresignedUrlUploader import PresignedUrlUploader
from bundlesubmissionclient.PrepareEsmdBundleSubmissionData import PrepareBundleSubmission
from bundlesubmissionclient.EsmdBundleSubmission import BundleSubmission
from bundlesubmissionclient.EsmdFhirBundleSubmissionResponseProcessor import FhirResponseProcessor


class PresignedUrlGenerator:
    """
    Enhanced presigned URL generator with comprehensive validation and error handling.
    
    Features:
    - Input validation
    - Retry logic
    - Proper error handling
    - Type safety
    - Performance monitoring
    """
    
    def __init__(
        self, 
        config_util: Optional[ConfigUtility] = None,
        auth_client: Optional[EsmdAuthClient] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize the PresignedUrlGenerator.
        
        Args:
            config_util: Configuration utility instance
            auth_client: Authentication client instance
            retry_config: Retry configuration for network operations
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Define log folder and file path
        log_folder = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_folder, exist_ok=True)  # Create folder if it doesn't exist


        
        self.config_util = config_util or ConfigUtility()
        self.auth_client = auth_client or EsmdAuthClient(self.config_util)
        self.logger = setup_logger(self.__class__.__name__)
        # Setup retry configuration
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            backoff_factor=1.0,
            retry_statuses=[500, 502, 503, 504, 429],
            timeout=30
        )
        
        # Load configuration
        try:
            self.base_url = self.config_util.get_fhir_server_url()
            self.presigned_base_url = self.config_util.get_presigned_url_base()
            self.timeout = self.config_util.get_timeout()
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
        
        self.logger.info(f"Initialized PresignedUrlGenerator with base URL: {self.base_url}")
    
    
    def validate_file_path(self, file_path: str) -> None:
        """
        Validate that a file path exists and is accessible.
        
        Args:
            file_path: Path to validate
            
        Raises:
            ValidationError: If file path is invalid
            FileOperationError: If file cannot be accessed
        """
        if not file_path or not file_path.strip():
            raise ValidationError("File path cannot be empty", field="file_path", value=file_path)
        
        # Validate path format
        path_validation = validate_file_path(file_path)
        if not path_validation.is_valid:
            raise ValidationError(
                f"Invalid file path format: {', '.join(path_validation.errors)}",
                field="file_path",
                value=file_path
            )
        
        # Check if file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileOperationError(
                f"File not found: {file_path}",
                file_path=file_path,
                operation="read"
            )
        
        if not file_path_obj.is_file():
            raise FileOperationError(
                f"Path is not a file: {file_path}",
                file_path=file_path,
                operation="read"
            )
        
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            raise FileOperationError(
                f"File is not readable: {file_path}",
                file_path=file_path,
                operation="read"
            )
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get the size of a file in bytes with validation.
        
        Args:
            file_path: Path to the file
            
        Returns:
            int: File size in bytes
            
        Raises:
            ValidationError: If file path is invalid
            FileOperationError: If file cannot be accessed
        """
        self.validate_file_path(file_path)
        
        try:
            size = os.path.getsize(file_path)
            if size < 0:
                raise FileOperationError(
                    f"Invalid file size: {size}",
                    file_path=file_path,
                    operation="size_check"
                )
            return size
        except OSError as e:
            raise FileOperationError(
                f"Error getting file size for {file_path}: {e}",
                file_path=file_path,
                operation="size_check"
            )
    
    def generate_md5(self, file_path: str) -> str:
        """
        Generate MD5 hash for a file with validation and error handling.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Base64 encoded MD5 hash
            
        Raises:
            ValidationError: If file path is invalid
            FileOperationError: If file cannot be accessed
        """
        self.validate_file_path(file_path)
        
        try:
            # Use utility function for MD5 calculation
            md5_hex = calculate_file_md5(file_path)
            
            # Convert to base64 for FHIR compatibility
            import base64
            import hashlib
            
            # Re-calculate for base64 encoding
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            md5_base64 = base64.b64encode(hash_md5.digest()).decode('utf-8')
            self.logger.debug(f"Generated MD5 for {file_path}: {md5_base64}")
            return md5_base64
            
        except Exception as e:
            raise FileOperationError(
                f"Error generating MD5 hash for {file_path}: {e}",
                file_path=file_path,
                operation="md5_generation"
            )
    
    def validate_presigned_url_request(
        self, 
        unique_id: str, 
        organizationid: str, 
        file_paths: List[str]
    ) -> ValidationResult:
        """
        Validate presigned URL request parameters.
        
        Args:
            unique_id: Unique identifier for the request
            organizationid: Sender organization identifier
            file_paths: List of file paths to upload
            
        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult(is_valid=True)
        
        # Validate unique_id
        if not unique_id or not unique_id.strip():
            result.errors.append("Unique ID cannot be empty")
        
        # Validate organizationid
        if not organizationid or not organizationid.strip():
            result.errors.append("OrganizationID cannot be empty")
        elif not organizationid.startswith('urn:oid:'):
            result.warnings.append("OrganizationID should start with 'urn:oid:'")

        # Validate file_paths
        if not file_paths:
            result.errors.append("File paths list cannot be empty")
        elif len(file_paths) > 50:  # Reasonable limit
            result.warnings.append("Large number of files may cause performance issues")
        
        # Validate each file path
        for i, file_path in enumerate(file_paths):
            try:
                self.validate_file_path(file_path)
            except (ValidationError, FileOperationError) as e:
                result.errors.append(f"File {i+1} ({file_path}): {str(e)}")
        
        result.is_valid = len(result.errors) == 0
        return result
    
    def _make_presigned_url_request(
        self, 
        unique_id: str, 
        organizationid: str, 
        file_paths: List[str]
    ) -> Dict[str, Any]:
        """
        Make the actual HTTP request for presigned URL generation.
        
        Args:
            unique_id: Unique identifier for the request
            organizationid: Sender organization identifier  
            file_paths: List of file paths to upload
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            AuthenticationError: If authentication fails
            NetworkError: If network request fails
            PresignedUrlError: If presigned URL generation fails
        """
        # Make request with retry logic
        @retry_with_backoff(self.retry_config)
        def _make_request():
            url = f"{self.presigned_base_url}/DocumentReference/$generate-presigned-url"

            # Get authentication header
            try:
                 auth_header = self.auth_client.get_auth_header()
            except Exception as e:
                raise AuthenticationError(f"Failed to get authentication token: {e}")
        
            headers = {
                **auth_header,
                'Content-Type': 'application/fhir+json',
                'Accept': 'application/fhir+json'
                }
        
        # Build FHIR Parameters resource
            parameters = {
                "resourceType": "Parameters",
                "id": sanitize_filename(unique_id),
                "parameter": [
                    {"name": "organizationid", "valueString": organizationid}
                ]
        }
        
        # Add file information
            for file_path in file_paths:
                try:
                    md5_hash = self.generate_md5(file_path)
                    if not md5_hash:
                        self.logger.warning(f"Skipping file {file_path} due to missing MD5 hash")
                        continue
                    filename = os.path.basename(file_path)
                    file_size = self.get_file_size(file_path)
                    file_size_in_mb = round(file_size / (1024 * 1024), 4)

                    file_param = {
                        "name": "fileinfo",
                        "part": [
                            {"name": "filename", "valueString": sanitize_filename(filename)},
                            {"name": "content-md5", "valueString": md5_hash},
                            {"name": "mimetype", "valueString": get_content_type(file_path)},
                            {"name": "filesize", "valueString": str(file_size_in_mb)}
                        ]
                }
                    parameters["parameter"].append(file_param)
                
                except Exception as e:
                    raise PresignedUrlError(
                        f"Failed to process file {file_path}: {e}",
                        file_paths=[file_path]
                )
        
        # Make request
        
            try:
                payload = json.dumps(parameters, indent=2)
                self.logger.debug(f"Sending presigned URL request to {url}")
            
                response = requests.post(
                    url, 
                    headers=headers, 
                    data=payload,
                    timeout=self.timeout
            )
            
            # Check response
                if response.status_code == 200:
                    response_data = response.json()
                    self.logger.info(f"Successfully generated presigned URLs for {len(file_paths)} files")
                    return response_data
                elif response.status_code == 401:
                    raise AuthenticationError(
                        "Authentication failed when generating presigned URLs",
                        token_endpoint=self.auth_client.auth_config.token_endpoint
                    )
                elif response.status_code >= 500:
                    raise NetworkError(
                        f"Server error generating presigned URLs: {response.status_code}",
                        url=url,
                        method="POST"
                )
                else:
                    raise PresignedUrlError(
                         f"Failed to generate presigned URLs. Status: {response.status_code}, Response: {response.text}",
                        file_paths=file_paths
                )
                
            except requests.exceptions.Timeout:
                raise NetworkError(
                    "Request timeout while generating presigned URLs",
                    url=url,
                    method="POST"
            )
            except requests.exceptions.ConnectionError as e:
                raise NetworkError(
                    f"Connection error while generating presigned URLs: {e}",
                    url=url,
                    method="POST"
            )
            except requests.exceptions.RequestException as e:
                raise NetworkError(
                    f"Network error while generating presigned URLs: {e}",
                    url=url,
                    method="POST"
            )
        return _make_request()
    
    def generate_presigned_url(
        self, 
        unique_id: str, 
        organizationid: str, 
        file_paths: List[str]
    ) -> Dict[str, Any]:
        """
        Generate presigned URLs for file uploads with comprehensive validation.
        
        Args:
            unique_id: Unique identifier for the request
            organizationid: Sender organization identifier
            file_paths: List of file paths to upload
            
        Returns:
            Dict[str, Any]: Response containing presigned URLs
            
        Raises:
            ValidationError: If input parameters are invalid
            PresignedUrlError: If presigned URL generation fails
            AuthenticationError: If authentication fails
            NetworkError: If network request fails
        """
        # Validate inputs
        validation = self.validate_presigned_url_request(unique_id, organizationid, file_paths)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid presigned URL request: {', '.join(validation.errors)}",
                field="request_parameters"
            )
        
        # Log warnings if any
        for warning in validation.warnings:
            self.logger.warning(warning)
        
        # Make request with retry logic
         # Exception handling block
        try:
     
            return self._make_presigned_url_request(unique_id, organizationid, file_paths)
        except RetryExhaustedError as e:
            self.logger.error(f"Presigned URL generation failed after retries: {e}")
            if hasattr(e, "last_exception") and e.last_exception:
                last_exc_msg = f" | Last error: {e.last_exception}"
            if isinstance(getattr(e, "last_exception", None), AuthenticationError):
                raise AuthenticationError(
            f"Authentication failed after retries: {e.last_exception}"
        ) from e
            elif isinstance(getattr(e, "last_exception", None), NetworkError):
                raise NetworkError(
            f"Network error after retries: {e.last_exception}"
        ) from e
        except (ValidationError, PresignedUrlError, AuthenticationError, NetworkError) as e:
            self.logger.error(f"Presigned URL generation failed: {e}")
            raise e
        except Exception as e:
            self.logger.error(f"Unexpected error in generate_presigned_url: {e}")
            raise PresignedUrlError(f"Unexpected error: {e}", file_paths=file_paths)
    
    def extract_filenames_and_tokens(self, response_data: Dict[str, Any]) -> List[Tuple[str, str]]:
            """
        Extract filenames and upload URLs from presigned URL response.
        
        Args:
            response_data: Response from presigned URL generation
            
        Returns:
            List[Tuple[str, str]]: List of (filename, upload_url) tuples
            
        Raises:
            ValidationError: If response format is invalid
            PresignedUrlError: If extraction fails
        """
            if not response_data:
                raise ValidationError("Response data cannot be empty", field="response_data")
        
            if not isinstance(response_data, dict):
                raise ValidationError(
                 "Response data must be a dictionary",
                    field="response_data",
                    value=type(response_data).__name__
            )
        
        
        
            try:
                parameters = response_data.get('parameter', [])
                if not parameters:
                    raise PresignedUrlError("No parameters found in response")
            
                extracted_data = []

                for parameter in parameters:
                    if parameter.get('name') == 'presignedUrls':
            # Loop through each file part under presignedUrls
                        for file_part in parameter.get('part', []):
                            if file_part.get('name') == 'file':
                                filename, upload_url = None, None
                                for part in file_part.get('part', []):
                                    param_name = part.get('name', '')
                                    if param_name == 'filename':
                                        filename = part.get('valueString')
                                    elif param_name == 'uploadUrl':
                                        upload_url = part.get('valueUrl')
                                if filename and upload_url:
                                    extracted_data.append((filename, upload_url))
                                else:
                                    self.logger.warning(f"Incomplete file info: filename={filename}, upload_url={upload_url}")
            
                if not extracted_data:
                    raise PresignedUrlError("No valid file information found in response")
            
                self.logger.info(f"Extracted {len(extracted_data)} file upload URLs")
                return extracted_data
            
            except Exception as e:
                if isinstance(e, PresignedUrlError):
                    raise e
                raise PresignedUrlError(f"Failed to extract file information from response: {e}")
    
    
    def generate_random_alphanumeric(self, length: int = 5) -> str:
        """
        Generate a random alphanumeric string.
        
        Args:
            length: Length of the string to generate
            
        Returns:
            str: Random alphanumeric string
            
        Raises:
            ValidationError: If length is invalid
        """
        if length <= 0:
            raise ValidationError("Length must be positive", field="length", value=length)
        
        if length > 100:  # Reasonable upper limit
            raise ValidationError("Length too large", field="length", value=length)
        
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    def create_file_upload_info(self, file_path: str, upload_url: str) -> FileUploadInfo:
        """
        Create FileUploadInfo object for a file.
        
        Args:
            file_path: Path to the file
            upload_url: Presigned URL for upload
            
        Returns:
            FileUploadInfo: File upload information
            
        Raises:
            ValidationError: If parameters are invalid
            FileOperationError: If file cannot be accessed
        """
        self.validate_file_path(file_path)
        
        if not upload_url or not upload_url.strip():
            raise ValidationError("Upload URL cannot be empty", field="upload_url", value=upload_url)
        
        return FileUploadInfo(
            file_path=file_path,
            presigned_url=upload_url,
            md5_hash=self.generate_md5(file_path),
            content_type=get_content_type(file_path),
            file_size=self.get_file_size(file_path)
        )
    
    def generate_presigned_urls_structured(
        self, 
        request: PresignedUrlRequest
    ) -> PresignedUrlResponse:
        """
        Generate presigned URLs using structured data models.
        
        Args:
            request: Presigned URL request
            
        Returns:
            PresignedUrlResponse: Structured response with file upload information
            
        Raises:
            ValidationError: If request is invalid
            PresignedUrlError: If generation fails
        """
        # Validate request
        if not request.file_paths:
            raise ValidationError("File paths cannot be empty in request")
        
        # Generate unique ID if not provided
        unique_id = f"presigned-{self.generate_random_alphanumeric(8)}"
        
        # Extract sender OID from metadata (assuming it's provided there)
        organizationid = request.metadata.get('organizationid')
        if not organizationid:
            raise ValidationError("organizationid must be provided in request metadata")
        
        # Generate presigned URLs
        response_data = self.generate_presigned_url(unique_id, organizationid, request.file_paths)
        
        # Extract file information
        file_info_tuples = self.extract_filenames_and_tokens(response_data)
        
        # Create structured file upload info
        upload_infos = []
        for filename, upload_url in file_info_tuples:
            # Find corresponding file path
            file_path = None
            for path in request.file_paths:
                if os.path.basename(path) == filename:
                    file_path = path
                    break
            
            if file_path:
                upload_info = self.create_file_upload_info(file_path, upload_url)
                upload_infos.append(upload_info)
        
        return PresignedUrlResponse(
            urls=upload_infos,
            transaction_id=unique_id
        )

    def entry_point(self, uniqueId, extensions_data, identifiers_data, filenames_with_path):
        """
        Entry point to handle the entire process from generating pre-signed URLs to uploading files, 
        building the bundle, and submitting it to the FHIR server.

        :param extensions_data: Dictionary with extension keys and values.
        :param identifiers_data: Dictionary with identifier keys and values.
        :param filenames_with_path: List of file paths to upload.
        """
        try:
            
            # Extract senderOid from extensions_data
            sender_oid = extensions_data.get("OrganizationIdValue")
            if not sender_oid:
                self.logger.error("OrganizationIdValue is missing from extensions_data.")
                return

            # Generate the pre-signed URL
            response = self.generate_presigned_url(uniqueId, sender_oid, filenames_with_path)
            if not response:
                self.logger.error("Failed to generate presigned URL")
                return

            result = self.extract_filenames_and_tokens(response)
            if not result:
                self.logger.error("Failed to extract filenames and upload URLs.")
                return

            uploader = PresignedUrlUploader()
            attachments = []
            dir_path = os.path.dirname(filenames_with_path[0])

            # Upload the files and prepare attachment data
            for filename, upload_url in result:
                file_path = os.path.join(dir_path, filename)
                file_size = self.get_file_size(file_path)
                md5_str = self.generate_md5(file_path)
                response_file = uploader.upload_file(upload_url, file_path, md5_str, file_size, content_type='application/xml')

                # Parse response and add attachment info
                data = json.loads(response_file)
                if data.get('status') == 'SUCCESS':
                    attachments.append({
                        "filename": data.get('filename'),
                        "uploaded_url": data.get('s3uri'),
                        "size": file_size,
                        "content_type": "application/pdf",
                        "hash_value": md5_str
                    })

            # Prepare and submit the bundle
            bundle_id = "bundle-" + self.generate_random_alphanumeric(5)
            list_id = "list-" + self.generate_random_alphanumeric(5)

            bundle_submission = PrepareBundleSubmission(bundle_id, list_id, extensions_data, identifiers_data, uniqueId)
            bundle_submission.add_document_reference("doc-001", attachments)
            final_bundle = bundle_submission.build_bundle()
            base_url = "https://dev.cpiapigateway.cms.gov/api/esmdf/v1/fhir/"
            submission = BundleSubmission(base_url)
            success, response = submission.submit_bundle(final_bundle)
            self.logger.info(f"FHIR Server response for bundle submission: {response}")
            # Handle both success and error cases
            if success:
                fhir_response = FhirResponseProcessor(response)
            else:
                # If error, response['response'] may be a dict or string
                resp_data = response.get('response') if isinstance(response, dict) else response
                fhir_response = FhirResponseProcessor(resp_data)
            result = fhir_response.process_response()
            if result.get("valid"):
                if result.get("transaction_id"):
                    self.logger.info(f"Transaction ID extracted: {result['transaction_id']}")
                    self.logger.info("Process completed successfully.")                    
            else:
                if result.get("transaction_id"):
                    self.logger.info(f"Transaction ID extracted: {result['transaction_id']}")
                self.logger.error("Validation Errors: {}".format(result.get("details", [])))
            return result
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred during processing: {e}")

# Example usage
if __name__ == "__main__":
    # Data for extensions and identifiers
    extensions_data = {
        "OrganizationId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-OrganizationId",
            "OrganizationIdValue": "urn:oid:123.456.657.126",
            "IntendedRecipient": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-IntendedRecipient",
            "IntendedRecipientValue": "urn:oid:2.16.840.1.113883.13.34.110.1.999.1",
            "LinesOfBusinessId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-LinesOfBusinessId",
            "LinesOfBusinessIdValue": "1",
            "ClaimId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ClaimId",
            "ClaimIdValue": "CLAIM1234567",
            "CaseId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-CaseId",
            "CaseIdValue": "CASE1234567",
            # "SplitNumber": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-SplitNumber",
            # "SplitNumberValue": "1-5",
            "AttachmentControlNumber": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-AttachmentControlNumber",
            "AttachmentControlNumberValue": "CONTROL123",
            "ResponseTypeCategory": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ResponseTypeCategory",
            "ResponseTypeCategoryValue": "RESPONSE_TYPE",
            "UniqueId" : "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-UniqueId",
            "UniqueIdValue": "UNIQUE1234567",
            "NPI": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-NPI",
            "NPIValue": "1234567890",
            "ParentUniqueId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ParentUniqueId",
            "ParentUniqueIdValue": "PARENT_UNIQUE1234567"

    }

    identifiers_data = {
        "UniqueIdSystem": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Idn-UniqueId",
        "UniqueIdValue": "UNIQUE1234569"
    }

    file_paths = [
        "tests/sample_files/realtimepayload1.xml",
        "tests/sample_files/realtimepayload2.xml"
    ]

    # Initialize the generator
    config = ConfigUtility()
    generator = PresignedUrlGenerator()
    unique_id = f"presigned-{generator.generate_random_alphanumeric(8)}"
    # Generate the pre-signed URL
    response = generator.entry_point(unique_id, extensions_data, identifiers_data, file_paths)

