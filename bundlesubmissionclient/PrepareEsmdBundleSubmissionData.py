from datetime import datetime
from datetime import datetime
from esmd_shared.logger import setup_logger
import pytz

class PrepareBundleSubmission:
    def __init__(self, bundle_id, list_id, extensions_data, identifiers_data, uniqueid):
        self.bundle_id = bundle_id
        self.list_id = list_id
        self.extensions_data = extensions_data
        self.identifiers_data = identifiers_data
        self.entries = []
        self.uniqueid= uniqueid

    

    def generate_fhir_timestamp(self):
        # Get the current time with timezone information
        tz = pytz.timezone('America/New_York')  # Change the timezone as needed
        current_time = datetime.now(tz)
        
        # Format the time according to FHIR standard
        fhir_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S%z')
        
        # Insert the colon in the timezone part to match the FHIR format (e.g., -0500 -> -05:00)
        fhir_timestamp = fhir_timestamp[:-2] + ':' + fhir_timestamp[-2:]
        
        return fhir_timestamp

    
    def add_document_reference(self, doc_id, attachments):
        """
        Adds a DocumentReference entry to the bundle for the uploaded documents with multiple attachments.
        
        :param doc_id: The document ID (e.g., UUID).
        :param attachments: A list of attachments, each represented by a dictionary containing filename, uploaded URL, size, content type, and hash value.
        """
        # Construct the content section with multiple attachments
        content_list = []
        for attachment in attachments:
            content_list.append({
                "attachment": {
                    "id": attachment.get("filename"),
                    "contentType": attachment.get("content_type", "application/xml"),
                    "url": attachment.get("uploaded_url"),
                    "size": attachment.get("size", 0),
                    "hash": attachment.get("hash_value", "2jmj7l5rSw0yVb/vlWAYkK/YBwk="),
                    "title": attachment.get("filename"),
                    "creation": self.generate_fhir_timestamp()
                },
                "format": {
                    "system": "https://terminology.esmddev.cms.gov:8099/fhir/CodeSystem/Esmd-CS-FormatCode",
                    "code": "urn:ihe:iti:xds-sd:pdf:2008"
                }
            })

        # Construct the document reference resource
        document_reference_entry = {
            "fullUrl": f"{doc_id}",
            "resource": {
                "resourceType": "DocumentReference",
                "id": f"{doc_id}",
                "meta": {
                    "profile": [
                        "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-DocumentReference"
                    ], "security": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
                        "code": "V",
                        "display": "Very-Restricted"
                    }]

                },
                "identifier": [
                    {
                        "system": self.identifiers_data.get("UniqueIdSystem"),
                        "value": self.uniqueid
                    }
                ],
                "status": "current",
                "date": self.generate_fhir_timestamp(),
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "47039-3",
                                "display": "Hospital Admission history and physical note"
                            }
                        ]
                    }
                ],
                "securityLabel": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
                                "code": "V",
                                "display": "Very-Restricted"
                            }
                        ]
                    }
                ],
                "content": content_list,
                "context": {
                    "facilityType": {
                        "coding": [
                            {
                                "system": "https://terminology.esmddev.cms.gov:8099/fhir/CodeSystem/Esmd-CS-FacilityTypeCodes",
                                "code": "hcp",
                                "display": "Health Care Provider"
                            }
                        ]
                    }
                }
            },
            "request": {
                "method": "POST",
                "url": "DocumentReference"
            }
        }

        # Add the document reference to the entries list
        self.entries.append(document_reference_entry)

    def build_bundle(self):
        """
        Build the complete BundleSubmission with all entries and extensions.
        
        :return: The final FHIR Bundle as a Python dictionary.
        """
        list_entry = {
            "fullUrl": f"{self.list_id}",
            "resource": {
                "resourceType": "List",
                "id": f"{self.list_id}",
                "meta": {
                    "profile": [
                        "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-ListSubmissionSet"
                    ],
                    "security": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
                        "code": "V",
                        "display": "Very-Restricted"
                    }]
                },
                "extension": [
                    {
                        "url": self.extensions_data.get("OrganizationId"),
                        "valueString": self.extensions_data.get("OrganizationIdValue")
                    },
                    {
                        "url": self.extensions_data.get("IntendedRecipient"),
                        "valueCode": self.extensions_data.get("IntendedRecipientValue")
                    },
                    {
                        "url": self.extensions_data.get("LinesOfBusinessId"),
                        "valueCode": self.extensions_data.get("LinesOfBusinessIdValue")
                    },
                    {
                        "url": self.extensions_data.get("NPI"),
                        "valueString": self.extensions_data.get("NPIValue")
                    },
                     {
                        "url": self.extensions_data.get("UniqueId"),
                        "valueString": self.uniqueid
                    }
                ],
                "identifier": [
                    {
                        "system": self.identifiers_data.get("UniqueIdSystem"),
                        "value": self.identifiers_data.get("UniqueIdValue")
                    }
                ],
                "status": "current",
                "mode": "working",
                "title": "Submission Set Title",
                "date": self.generate_fhir_timestamp(),
                "entry": [
                    {
                        "item": {
                            "reference": f"DocumentReference/{self.entries[0]['resource']['id']}"
                        }
                    }
                ]
            },
            "request": {
                "method": "POST",
                "url": "List"
            }
        }

        # Conditionally add optional elements
        if self.extensions_data.get("CaseIdValue"):
            list_entry["resource"]["extension"].append({
                "url": self.extensions_data.get("CaseId"),
                "valueString": self.extensions_data.get("CaseIdValue")
            })

        if self.extensions_data.get("SplitNumberValue"):
            list_entry["resource"]["extension"].append({
                "url": self.extensions_data.get("SplitNumber"),
                "valueString": self.extensions_data.get("SplitNumberValue")
            })

        if self.extensions_data.get("ClaimIdValue"):
            list_entry["resource"]["extension"].append({
                "url": self.extensions_data.get("ClaimId"),
                "valueString": self.extensions_data.get("ClaimIdValue")
            })

        
        if self.extensions_data.get("AttachmentControlNumberValue"):
            list_entry["resource"]["extension"].append({
                "url": self.extensions_data.get("AttachmentControlNumber"),
                "valueString": self.extensions_data.get("AttachmentControlNumberValue")
            })

        if self.extensions_data.get("ResponseTypeCategoryValue"):
            list_entry["resource"]["extension"].append({
                "url": self.extensions_data.get("ResponseTypeCategory"),
                "valueString": self.extensions_data.get("ResponseTypeCategoryValue")
            })

        if self.extensions_data.get("ParentUniqueIdValue"):
            list_entry["resource"]["identifier"].append({
                "system": self.extensions_data.get("ParentUniqueIdSystem"),
                "value": self.extensions_data.get("ParentUniqueIdValue")
            })
        if self.extensions_data.get("SplitNumberValue"):
            list_entry["resource"]["identifier"].append({
                "system": self.extensions_data.get("SplitNumber"),
                "value": self.extensions_data.get("SplitNumberValue")
            })

        # Build the complete bundle
        bundle = {
            "resourceType": "Bundle",
            "id": f"{self.bundle_id}",
            "meta": {
                "profile": [
                    "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-BundleSubmission"
                ],
                "security": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
                    "code": "V",
                    "display": "very restricted"
                }]
            },
            "type": "transaction",
            "timestamp": self.generate_fhir_timestamp(),
            "entry": [list_entry]
        }

        # Add all document references to the bundle
        bundle['entry'].extend(self.entries)
        
        return bundle

# Example Usage
if __name__ == "__main__":
    # Example input data
    bundle_id = "bundle-001"
    list_id = "list-001"
    doc_id = "doc-001"

    # Example extension and identifier data
    extensions_data = {
        "SenderOid": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-SenderOid",
        "SenderOidValue": "urn:oid:1.2.840.10008.3.1.2.1.1",
        "IntendedRecipient": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-IntendedRecipient",
        "IntendedRecipientValue": "urn:oid:2.16.840.1.113883.13.34.110.1.100.23",
        "LinesOfBusinessId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-LinesOfBusinessId",
        "LinesOfBusinessIdValue": "1",
        "ClaimId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ClaimId",
        "ClaimIdValue": "CLAIM1234567",
        "CaseId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-CaseId",
        "CaseIdValue": "CASE1234567",  
        "SplitNumber": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-SplitNumber",
        "SplitNumberValue": "1-5",
        "NpiSystem": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-NPI",
        "NpiValue": "1234567890"
    }

    identifiers_data = {
        "UniqueIdSystem": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-UniqueId",
        "UniqueIdValue": "UNIQUE1234569",
              
    }

    # Initialize the bundle submission utility
    bundle_submission = PrepareBundleSubmission(bundle_id, list_id, extensions_data, identifiers_data)

    # Add multiple attachments to a single DocumentReference after uploading them to esMD
    attachments = [
        {"filename": "file1.xml", "uploaded_url": "s3://bucket/file1.xml", "size": 1024, "content_type": "application/xml", "hash_value": "hash1"},
        {"filename": "file2.xml", "uploaded_url": "s3://bucket/file2.xml", "size": 2048, "content_type": "application/xml", "hash_value": "hash2"}
    ]
    bundle_submission.add_document_reference("doc-001", attachments)

    # Build the bundle
    final_bundle = bundle_submission.build_bundle()

    # Output the final bundle (you can print or log it)
    print(final_bundle)
