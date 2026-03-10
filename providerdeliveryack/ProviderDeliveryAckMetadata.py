from datetime import datetime
import uuid
from zoneinfo import ZoneInfo
from esmd_shared.logger import setup_logger  # Use shared logger
from esmd_shared.models import ProviderDeliveryAckMetadata  # Import the shared ProviderDeliveryAckMetadata model
from esmd_shared.config import ConfigUtility
class ProviderDeliveryAckMetadataHandler:
    def __init__(self, metadata: ProviderDeliveryAckMetadata):
        self.metadata = metadata
        self.logger = setup_logger(self.__class__.__name__)
        self.logger.info(f"Initialized {self.__class__.__name__} with metadata: {self.metadata}")
        self.logger.debug(f"ProviderDeliveryAckMetadata: {self.metadata}")
        self.config_util = ConfigUtility()
        self.terminology_base_url = self.config_util.get_fhir_terminology_server_url()


# Create a FHIR LIST resource using ProviderDeliveryACK metadata
    def create_list(self):
        self.logger.info(f"Creating FHIR LIST resource with metadata: {self.metadata}")
        # Implementation for creating the FHIR LIST resource goes here      
        list_id = str(uuid.uuid4())

        list = {
            "resourceType": "List",
            "id": list_id,
            "meta": {
                "profile": [
                    f"{self.terminology_base_url}/fhir/StructureDefinition/Esmd-ListDeliveryConfirmation"
                ],
                "security": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
                        "code": "V",
                        "display": "very restricted"
                    }
                ]
            }
        }
       
        # Add extensions if present
        extensions = []
        if getattr(self.metadata, 'transaction_id', None):
            extensions.append({
                "url": f"{self.terminology_base_url}/fhir/StructureDefinition/Esmd-Ext-TransactionId",
                "valueString": self.metadata.transaction_id
            })
        if getattr(self.metadata, 'organization_id', None):
            extensions.append({
                "url": f"{self.terminology_base_url}/fhir/StructureDefinition/Esmd-Ext-OrganizationId",
                "valueString": self.metadata.organization_id
            })
        if getattr(self.metadata, 'npi', None):
            extensions.append({
                "url": f"{self.terminology_base_url}/fhir/StructureDefinition/Esmd-Ext-NPI",
                "valueString": self.metadata.npi
            })
        if getattr(self.metadata, 'delivery_datetime', None):
            extensions.append({
                "url": f"{self.terminology_base_url}/fhir/StructureDefinition/Esmd-Ext-DeliveryDateTime",
                "valueDateTime": self.metadata.delivery_datetime
            })
        
        
        if extensions:
            list["extension"] = extensions
        list["status"] = "current"
        list["mode"] = "working"
        list["title"] = "Provider Delivery Acknowledgment"
        est_now = datetime.now(ZoneInfo("America/New_York"))
        list["date"] = est_now.isoformat()

        # Add contained OperationOutcome resource
        diagnostics_text = getattr(self.metadata, "diagnostics", None) or "ok"
        severity = getattr(self.metadata, "severity", None) or "information"
        code = getattr(self.metadata, "code", None) or "informational"

        operationOutcome_id = f"{getattr(self.metadata, 'transaction_id', None)}-OperationOutcome"
        contained_op = {
            "resourceType": "OperationOutcome",
            "id": operationOutcome_id,
            "meta": {
                "profile": [
                    f"{self.terminology_base_url}/fhir/StructureDefinition/Esmd-OperationOutcome"
                ]
            },
            "issue": [
                {
                    "severity": severity,
                    "code": code,
                    "diagnostics": diagnostics_text
                }
            ]
        }
        list["contained"] = [contained_op]

        entry = [
            {
                "item": {
                    "reference": f"#{self.metadata.transaction_id}-OperationOutcome"
                }
            }
        ]
        list["entry"] = entry

        self.logger.info(f"Practitioner created with ID: {list_id} and PractitionerResource is {list}")
        return list
        self.logger.debug(f"FHIR LIST resource created successfully.")


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
