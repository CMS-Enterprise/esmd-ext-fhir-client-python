from datetime import datetime
import uuid
import logging
import json
from esmd_shared.logger import setup_logger  # Use shared logger
from esmd_shared.models import PractitionerMetadata    # Import the shared PractitionerMetadata model

# class PractitionerMetadata:
#     def __init__(self, first_name, last_name, gender, npi, provider_number, provider_taxid, action_requested, service_code, service_start_date, service_end_date):
#         self.first_name = first_name
#         self.last_name = last_name
#         self.gender = gender
#         self.npi = npi
#         self.provider_number = provider_number
#         self.provider_taxid = provider_taxid
#         self.action_requested = action_requested
#         self.service_code = service_code
#         self.service_start_date = service_start_date
#         self.service_end_date = service_end_date
#         # Set up the logger for this class using the common logger
#         self.logger = setup_logger(self.__class__.__name__)

class PreparePractitionerAndBundlePractitioner:
    def __init__(self, practitioner_metadata):
            self.practitioner_metadata = practitioner_metadata
            # Set up the logger for this class using the common logger
            self.logger = setup_logger(self.__class__.__name__)

    # Create a FHIR Practitioner resource using practitioner metadata
    def create_practitioner(self):
        practitioner_id = str(uuid.uuid4())

        practitioner = {
            "resourceType": "Practitioner",
            "id": practitioner_id,
            "meta": {
                "profile": [
                    "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Practitioner"
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
        # Add telecom if present
        if getattr(self.practitioner_metadata, 'telecom', None):
            practitioner["telecom"] = self.practitioner_metadata.telecom
        # Add name if present
        name = {}
        if getattr(self.practitioner_metadata, 'family_name', None):
            name["family"] = self.practitioner_metadata.family_name
        if getattr(self.practitioner_metadata, 'given_name', None):
            name["given"] = self.practitioner_metadata.given_name
        name["prefix"] = ["Dr"]
        if name:
            practitioner["name"] = [name]
        # Add extensions if present
        extensions = []
        if getattr(self.practitioner_metadata, 'action_requested', None):
            extensions.append({
                "url": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ActionRequestedCode",
                "valueCode": self.practitioner_metadata.action_requested
            })
        if getattr(self.practitioner_metadata, 'service_code', None):
            extensions.append({
                "url": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ServiceCode",
                "valueCode": self.practitioner_metadata.service_code
            })
        if getattr(self.practitioner_metadata, 'service_start_date', None):
            extensions.append({
                "url": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ServiceStartDate",
                "valueDate": self.practitioner_metadata.service_start_date
            })
        if getattr(self.practitioner_metadata, 'service_end_date', None):
            extensions.append({
                "url": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ServiceEndDate",
                "valueDate": self.practitioner_metadata.service_end_date
            })
        if getattr(self.practitioner_metadata, 'npi', None):
            extensions.append({
                "url": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-NPI",
                "valueString": self.practitioner_metadata.npi
            })
        if getattr(self.practitioner_metadata, 'provider_taxid', None):
            extensions.append({
                "url": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ProviderTaxId",
                "valueString": self.practitioner_metadata.provider_taxid
            })
        if getattr(self.practitioner_metadata, 'provider_number', None):
            extensions.append({
                "url": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ProviderNumber",
                "valueString": self.practitioner_metadata.provider_number
            })
        
        if extensions:
            practitioner["extension"] = extensions
        practitioner["active"] = getattr(self.practitioner_metadata, 'active', True)
        practitioner["created"] = datetime.now().isoformat()
        if getattr(self.practitioner_metadata, 'gender', None):
            practitioner["gender"] = self.practitioner_metadata.gender
        
        self.logger.info(f"Practitioner created with ID: {practitioner_id} and PractitionerResource is {practitioner}")
        return practitioner

    # Create a Bundle with multiple Practitioner resources
    @staticmethod
    def create_practitioner_bundle(practitioners):
        bundle_id = str(uuid.uuid4())

        bundle = {
            "resourceType": "Bundle",
            "id": bundle_id,
            "type": "batch",  # Set the Bundle type to 'batch',
            "meta": {
                "profile": ["https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-BundleServiceRegistration"],
                "security": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
                    "code": "V",
                    "display": "very restricted"
                }]
      },
            "entry": []
        }

        for practitioner in practitioners:
            bundle["entry"].append({
                "fullUrl": f"urn:uuid:{practitioner['id']}",
                "resource": practitioner,
                "request": {
                    "method": "POST",
                    "url": f"Practitioner/{practitioner['id']}"
                }
            })

        logging.info(f"Bundle created with ID: {bundle_id} and {len(practitioners)} practitioners")
        return bundle

if __name__ == "__main__":
    # Create PractitionerMetadata dataclass instances
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
        action_requested="R",
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

    practitioner1 = prep1.create_practitioner()
    practitioner2 = prep2.create_practitioner()

    practitioners = [practitioner1, practitioner2]
    bundle = PreparePractitionerAndBundlePractitioner.create_practitioner_bundle(practitioners)
    print(json.dumps(bundle, indent=2))
