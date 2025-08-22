"""
Unit tests for PrepareBundleSubmission in bundlesubmissionclient module.
"""

import pytest
import re
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from bundlesubmissionclient.PrepareEsmdBundleSubmissionData import PrepareBundleSubmission


@pytest.fixture
def sample_extensions_data():
    """Sample extensions data for testing."""
    return {
        "OrganizationId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-OrganizationId",
        "OrganizationIdValue": "urn:oid:1.2.3.4.5",
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
        "AttachmentControlNumber": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-AttachmentControlNumber",
        "AttachmentControlNumberValue": "CONTROL123",
        "ResponseTypeCategory": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ResponseTypeCategory",
        "ResponseTypeCategoryValue": "RESPONSE_TYPE",
        "UniqueId" : "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-UniqueId",
        "UniqueIdValue": "UNIQUE1234567",
        "NPI": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-NPI",
        "NPIValue": "1234567890"
    }

@pytest.fixture
def sample_identifiers_data():
    """Sample identifiers data for testing."""
    return {
        "UniqueIdSystem": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Idn-UniqueId",
        "UniqueIdValue": "UNIQUE1234569"
    }

@pytest.fixture
def sample_attachments():
    """Sample attachments data for testing."""
    return [
        {
            "filename": "document1.xml",
            "uploaded_url": "https://s3.amazonaws.com/bucket/document1.xml",
            "size": 1024,
            "content_type": "application/xml",
            "hash_value": "hash1value"
        },
        {
            "filename": "document2.xml", 
            "uploaded_url": "https://s3.amazonaws.com/bucket/document2.xml",
            "size": 2048,
            "content_type": "application/xml",
            "hash_value": "hash2value"
        }
    ]

class TestPrepareBundleSubmission:
    """Test cases for PrepareBundleSubmission class."""
    
    @pytest.fixture
    def bundle_submission(self, sample_extensions_data, sample_identifiers_data):
        """Create PrepareBundleSubmission instance for testing."""
        return PrepareBundleSubmission(
            "test-bundle-001",
            "test-list-001", 
            sample_extensions_data,
            sample_identifiers_data,
            "unique-id-001"
        )
    
    def test_init(self, bundle_submission, sample_extensions_data, sample_identifiers_data):
        """Test PrepareBundleSubmission initialization."""
        assert bundle_submission.bundle_id == "test-bundle-001"
        assert bundle_submission.list_id == "test-list-001"
        assert bundle_submission.extensions_data == sample_extensions_data
        assert bundle_submission.identifiers_data == sample_identifiers_data
        assert bundle_submission.entries == []
        assert bundle_submission.uniqueid == "unique-id-001"
    
    def test_generate_fhir_timestamp_format(self, bundle_submission):
        """Test FHIR timestamp generation format."""
        timestamp = bundle_submission.generate_fhir_timestamp()
        
        # Verify timestamp format (YYYY-MM-DDTHH:MM:SS+/-HH:MM)
        fhir_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$'
        assert re.match(fhir_pattern, timestamp), f"Invalid FHIR timestamp format: {timestamp}"
    
    def test_generate_fhir_timestamp_timezone(self, bundle_submission):
        """Test FHIR timestamp includes timezone information."""
        timestamp = bundle_submission.generate_fhir_timestamp()
        
        # Should have timezone offset
        assert '+' in timestamp or '-' in timestamp[-6:]
        assert ':' in timestamp[-3:]  # Colon in timezone offset
    
    def test_generate_fhir_timestamp_consistency(self, bundle_submission):
        """Test FHIR timestamp generation consistency within short time window."""
        timestamp1 = bundle_submission.generate_fhir_timestamp()
        timestamp2 = bundle_submission.generate_fhir_timestamp()
        
        # Timestamps should be very close (within same minute for this test)
        assert timestamp1[:16] == timestamp2[:16]  # Compare up to minutes
    
    @patch('bundlesubmissionclient.PrepareEsmdBundleSubmissionData.datetime')
    def test_generate_fhir_timestamp_mocked_datetime(self, mock_datetime, bundle_submission):
        """Test FHIR timestamp with mocked datetime."""
        # Mock datetime to return a specific time
        mock_time = Mock()
        mock_time.strftime.return_value = "2023-12-01T10:30:45-0500"
        mock_datetime.now.return_value = mock_time
        
        timestamp = bundle_submission.generate_fhir_timestamp()
        
        assert timestamp == "2023-12-01T10:30:45-05:00"
    
    def test_add_document_reference_single_attachment(self, bundle_submission):
        """Test adding document reference with single attachment."""
        attachments = [{
            "filename": "test_doc.xml",
            "uploaded_url": "https://s3.amazonaws.com/bucket/test_doc.xml",
            "size": 1024,
            "content_type": "application/xml",
            "hash_value": "testhash123"
        }]
        
        bundle_submission.add_document_reference("doc-001", attachments)
        
        assert len(bundle_submission.entries) == 1
        
        entry = bundle_submission.entries[0]
        assert entry["fullUrl"] == "doc-001"
        assert entry["resource"]["resourceType"] == "DocumentReference"
        assert entry["resource"]["id"] == "doc-001"
        assert len(entry["resource"]["content"]) == 1
        
        content = entry["resource"]["content"][0]
        assert content["attachment"]["id"] == "test_doc.xml"
        assert content["attachment"]["contentType"] == "application/xml"
        assert content["attachment"]["url"] == "https://s3.amazonaws.com/bucket/test_doc.xml"
        assert content["attachment"]["size"] == 1024
        assert content["attachment"]["hash"] == "testhash123"
        assert content["attachment"]["title"] == "test_doc.xml"
    
    def test_add_document_reference_multiple_attachments(self, bundle_submission, sample_attachments):
        """Test adding document reference with multiple attachments."""
        bundle_submission.add_document_reference("doc-002", sample_attachments)
        
        assert len(bundle_submission.entries) == 1
        
        entry = bundle_submission.entries[0]
        assert len(entry["resource"]["content"]) == 2
        
        # Check first attachment
        content1 = entry["resource"]["content"][0]
        assert content1["attachment"]["id"] == "document1.xml"
        assert content1["attachment"]["size"] == 1024
        
        # Check second attachment  
        content2 = entry["resource"]["content"][1]
        assert content2["attachment"]["id"] == "document2.xml"
        assert content2["attachment"]["size"] == 2048
    
    def test_add_document_reference_default_values(self, bundle_submission):
        """Test adding document reference with default values for missing fields."""
        attachments = [{
            "filename": "minimal_doc.xml",
            "uploaded_url": "https://s3.amazonaws.com/bucket/minimal_doc.xml"
            # Missing size, content_type, hash_value
        }]
        
        bundle_submission.add_document_reference("doc-003", attachments)
        
        entry = bundle_submission.entries[0]
        content = entry["resource"]["content"][0]
        
        # Should use default values
        assert content["attachment"]["contentType"] == "application/xml"  # Default
        assert content["attachment"]["size"] == 0  # Default
        assert content["attachment"]["hash"] == "2jmj7l5rSw0yVb/vlWAYkK/YBwk="  # Default
    
    def test_add_document_reference_structure_validation(self, bundle_submission, sample_attachments):
        """Test document reference structure validation."""
        bundle_submission.add_document_reference("doc-004", sample_attachments)
        
        entry = bundle_submission.entries[0]
        resource = entry["resource"]
        
        # Validate required fields
        assert resource["resourceType"] == "DocumentReference"
        assert "id" in resource
        assert "meta" in resource
        assert "identifier" in resource
        assert resource["status"] == "current"
        assert "date" in resource
        assert "category" in resource
        assert "securityLabel" in resource
        assert "content" in resource
        assert "context" in resource
        
        # Validate meta profile
        assert len(resource["meta"]["profile"]) == 1
        assert "Esmd-DocumentReference" in resource["meta"]["profile"][0]
        
        # Validate identifier structure
        assert len(resource["identifier"]) == 1
        assert "system" in resource["identifier"][0]
        assert "value" in resource["identifier"][0]
        
        # Validate category structure
        assert len(resource["category"]) == 1
        assert "coding" in resource["category"][0]
        assert resource["category"][0]["coding"][0]["system"] == "http://loinc.org"
        assert resource["category"][0]["coding"][0]["code"] == "47039-3"
        
        # Validate security label
        assert len(resource["securityLabel"]) == 1
        assert resource["securityLabel"][0]["coding"][0]["code"] == "V"
        
        # Validate context
        assert "facilityType" in resource["context"]
        assert resource["context"]["facilityType"]["coding"][0]["code"] == "hcp"
    
    def test_add_document_reference_request_structure(self, bundle_submission, sample_attachments):
        """Test document reference request structure."""
        bundle_submission.add_document_reference("doc-005", sample_attachments)
        
        entry = bundle_submission.entries[0]
        
        # Validate request structure
        assert "request" in entry
        assert entry["request"]["method"] == "POST"
        assert entry["request"]["url"] == "DocumentReference"
    
    def test_add_multiple_document_references(self, bundle_submission, sample_attachments):
        """Test adding multiple document references."""
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        bundle_submission.add_document_reference("doc-002", sample_attachments)
        
        assert len(bundle_submission.entries) == 2
        assert bundle_submission.entries[0]["resource"]["id"] == "doc-001"
        assert bundle_submission.entries[1]["resource"]["id"] == "doc-002"
    
    def test_build_bundle_basic_structure(self, bundle_submission, sample_attachments):
        """Test basic bundle structure building."""
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        
        bundle = bundle_submission.build_bundle()
        
        # Validate top-level bundle structure
        assert bundle["resourceType"] == "Bundle"
        assert bundle["id"] == "test-bundle-001"
        assert "meta" in bundle
        assert bundle["type"] == "transaction"
        assert "timestamp" in bundle
        assert "entry" in bundle
        
        # Should have 2 entries: List + DocumentReference
        assert len(bundle["entry"]) == 2
    
    def test_build_bundle_meta_structure(self, bundle_submission, sample_attachments):
        """Test bundle meta structure."""
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        
        bundle = bundle_submission.build_bundle()
        meta = bundle["meta"]
        
        # Validate meta profile
        assert "profile" in meta
        assert len(meta["profile"]) == 1
        assert "Esmd-BundleSubmission" in meta["profile"][0]
        
        # Validate security
        assert "security" in meta
        assert len(meta["security"]) == 1
        
        security_codes = [sec["code"] for sec in meta["security"]]
        assert "V" in security_codes
    
    def test_build_bundle_list_entry_structure(self, bundle_submission, sample_attachments):
        """Test List entry structure in bundle."""
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        
        bundle = bundle_submission.build_bundle()
        list_entry = bundle["entry"][0]
        
        # Validate List entry structure
        assert list_entry["fullUrl"] == "test-list-001"
        assert list_entry["resource"]["resourceType"] == "List"
        assert list_entry["resource"]["id"] == "test-list-001"
        assert list_entry["resource"]["status"] == "current"
        assert list_entry["resource"]["mode"] == "working"
        assert list_entry["resource"]["title"] == "Submission Set Title"
        
        # Validate request
        assert list_entry["request"]["method"] == "POST"
        assert list_entry["request"]["url"] == "List"
    
    def test_build_bundle_list_extensions(self, bundle_submission, sample_attachments):
        """Test List extensions in bundle."""
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        
        bundle = bundle_submission.build_bundle()
        list_resource = bundle["entry"][0]["resource"]
        
        # Should have required extensions plus optional ones
        extensions = list_resource["extension"]
        assert len(extensions) >= 3  # At least the required ones
        
        # Check required extensions
        extension_urls = [ext["url"] for ext in extensions]
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-OrganizationId" in extension_urls
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-IntendedRecipient" in extension_urls
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-LinesOfBusinessId" in extension_urls

        # Check optional extensions that should be present
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ClaimId" in extension_urls
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-CaseId" in extension_urls
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-SplitNumber" in extension_urls
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-AttachmentControlNumber" in extension_urls
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-ResponseTypeCategory" in extension_urls
    
    def test_build_bundle_list_identifiers(self, bundle_submission, sample_attachments):
        """Test List identifiers in bundle."""
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        
        bundle = bundle_submission.build_bundle()
        list_resource = bundle["entry"][0]["resource"]
        
        # Should have at least 2 identifiers + optional parent unique id
        identifiers = list_resource["identifier"]
        assert len(identifiers) >= 2
        
        # Check required identifiers
        identifier_systems = [ident["system"] for ident in identifiers]
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Idn-UniqueId" in identifier_systems        
       
    
    def test_build_bundle_list_entry_reference(self, bundle_submission, sample_attachments):
        """Test List entry reference to document."""
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        
        bundle = bundle_submission.build_bundle()
        list_resource = bundle["entry"][0]["resource"]
        
        # Should reference the document
        assert len(list_resource["entry"]) == 1
        assert list_resource["entry"][0]["item"]["reference"] == "DocumentReference/doc-001"
    
    def test_build_bundle_without_optional_extensions(self, sample_identifiers_data):
        """Test bundle building without optional extensions."""
        # Create minimal extensions data
        minimal_extensions = {
            "OrganizationId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-OrganizationId",
            "OrganizationIdValue": "urn:oid:1.2.3.4.5",
            "IntendedRecipient": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-IntendedRecipient",
            "IntendedRecipientValue": "urn:oid:2.16.840.1.113883.13.34.110.1.100.23",
            "LinesOfBusinessId": "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-LinesOfBusinessId",
            "LinesOfBusinessIdValue": "1"
        }
        
        bundle_submission = PrepareBundleSubmission(
            "minimal-bundle", "minimal-list", minimal_extensions, sample_identifiers_data, 'uniqued-id-001'
        )
        
        bundle_submission.add_document_reference("doc-001", [{
            "filename": "test.xml",
            "uploaded_url": "https://s3.amazonaws.com/test.xml",
            "size": 1024,
            "content_type": "application/xml",
            "hash_value": "hash123"
        }])
        
        bundle = bundle_submission.build_bundle()
        list_resource = bundle["entry"][0]["resource"]
        
        # Should only have required extensions
        assert len(list_resource["extension"]) >= 5
        
        extension_urls = [ext["url"] for ext in list_resource["extension"]]
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-OrganizationId" in extension_urls
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-IntendedRecipient" in extension_urls
        assert "https://terminology.esmddev.cms.gov:8099/fhir/StructureDefinition/Esmd-Ext-LinesOfBusinessId" in extension_urls

    def test_build_bundle_empty_entries_error(self, bundle_submission):
        """Test bundle building without any document references."""
        with pytest.raises(IndexError):
            # Should fail because it tries to access self.entries[0]
            bundle_submission.build_bundle()
    
    def test_build_bundle_timestamp_consistency(self, bundle_submission, sample_attachments):
        """Test that bundle timestamp is consistent with document reference timestamps."""
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        
        bundle = bundle_submission.build_bundle()
        
        bundle_timestamp = bundle["timestamp"]
        list_timestamp = bundle["entry"][0]["resource"]["date"]
        doc_timestamp = bundle["entry"][1]["resource"]["date"]
        
        # All timestamps should be in the same minute (close enough for test)
        assert bundle_timestamp[:16] == list_timestamp[:16]
        assert bundle_timestamp[:16] == doc_timestamp[:16]


@pytest.mark.integration
class TestPrepareBundleSubmissionIntegration:
    """Integration tests for PrepareBundleSubmission."""
    
    def test_complete_workflow(self, sample_extensions_data, sample_identifiers_data, sample_attachments):
        """Test complete workflow from initialization to bundle building."""
        bundle_submission = PrepareBundleSubmission(
            "integration-bundle-001",
            "integration-list-001",
            sample_extensions_data,
            sample_identifiers_data,
            'integration-unique-id-001'
        )
        
        # Add multiple document references
        bundle_submission.add_document_reference("doc-001", sample_attachments)
        bundle_submission.add_document_reference("doc-002", sample_attachments[:1])  # Single attachment
        
        # Build final bundle
        bundle = bundle_submission.build_bundle()
        
        # Validate complete bundle structure
        assert bundle["resourceType"] == "Bundle"
        assert len(bundle["entry"]) == 3  # List + 2 DocumentReferences
        
        # Validate all entries have proper request structures
        for entry in bundle["entry"]:
            assert "request" in entry
            assert entry["request"]["method"] == "POST"
            assert entry["request"]["url"] in ["List", "DocumentReference"]
    
    def test_real_timestamp_generation(self, sample_extensions_data, sample_identifiers_data):
        """Test with real timestamp generation (no mocking)."""
        bundle_submission = PrepareBundleSubmission(
            "real-time-bundle",
            "real-time-list", 
            sample_extensions_data,
            sample_identifiers_data,
            'real-time-unique-id'
        )
        
        timestamp = bundle_submission.generate_fhir_timestamp()
        
        # Should be valid FHIR timestamp format
        fhir_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$'
        assert re.match(fhir_pattern, timestamp)
        
        # Should be recent (within last minute)
        import pytz
        from datetime import datetime, timedelta
        tz = pytz.timezone('America/New_York')
        current_time = datetime.now(tz)
        
        # Parse timestamp and ensure timezone is set
        timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if timestamp_dt.tzinfo is None:
            timestamp_dt = tz.localize(timestamp_dt)
        else:
            timestamp_dt = timestamp_dt.astimezone(tz)

        time_diff = abs((current_time - timestamp_dt).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_large_attachment_list(self, sample_extensions_data, sample_identifiers_data):
        """Test with large number of attachments."""
        bundle_submission = PrepareBundleSubmission(
            "large-bundle",
            "large-list",
            sample_extensions_data,
            sample_identifiers_data,
            "large-unique-id-001"
        )
        
        # Create many attachments
        large_attachments = []
        for i in range(50):
            large_attachments.append({
                "filename": f"document_{i}.xml",
                "uploaded_url": f"https://s3.amazonaws.com/bucket/document_{i}.xml",
                "size": 1024 * (i + 1),
                "content_type": "application/xml",
                "hash_value": f"hash_{i}"
            })
        
        bundle_submission.add_document_reference("doc-large", large_attachments)
        bundle = bundle_submission.build_bundle()
        
        # Should handle large attachment list
        doc_entry = bundle["entry"][1]  # DocumentReference entry
        assert len(doc_entry["resource"]["content"]) == 50