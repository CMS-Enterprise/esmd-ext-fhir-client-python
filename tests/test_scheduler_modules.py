"""
Unit tests for scheduler modules in documentrefscheduler and notificationscheduler.
"""

import pytest
import json
import requests
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
from documentrefscheduler.EsmdDocumentRefLettersPullScheduler import DocumentRefLettersPullScheduler
from documentrefscheduler.EsmdFhirDocumentReferenceDataProcessor import FhirDocumentReferenceDataProcessor
from documentrefscheduler.EsmdFindDocRefUtility import FindDocRefUtility
from documentrefscheduler.EsmdBinaryFileExtractor import BinaryFileExtractor
from notificationscheduler.EsmdTransactionNotificationScheduler import TransactionNotificationScheduler
from notificationscheduler.EsmdFindListTransNotificationUtility import FindListTransNotificationUtility


class TestDocumentRefLettersPullScheduler:
    """Test cases for DocumentRefLettersPullScheduler class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('documentrefscheduler.EsmdDocumentRefLettersPullScheduler.setup_logger') as mock_logger, \
             patch('documentrefscheduler.EsmdDocumentRefLettersPullScheduler.ConfigUtility') as mock_config, \
             patch('documentrefscheduler.EsmdDocumentRefLettersPullScheduler.EsmdAuthClient') as mock_auth:
            
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config_instance.get_oid.return_value = "urn:oid:1.2.3.4.5"
            mock_config.return_value = mock_config_instance
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_access_token"
            mock_auth.return_value = mock_auth_instance
            
            yield {
                'logger': mock_logger,
                'config': mock_config_instance,
                'auth': mock_auth_instance
            }
    
    @pytest.fixture
    def scheduler(self, mock_dependencies):
        """Create DocumentRefLettersPullScheduler instance."""
        return DocumentRefLettersPullScheduler()
    
    def test_init(self, scheduler, mock_dependencies):
        """Test DocumentRefLettersPullScheduler initialization."""
        assert scheduler.base_url == "http://test-server:9012/fhir"
        assert scheduler.config_util is not None
        assert scheduler.auth_client is not None
    
    @patch('documentrefscheduler.EsmdDocumentRefLettersPullScheduler.requests.get')
    def test_fetch_document_references_success(self, mock_get, scheduler):
        """Test successful document reference fetching."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Bundle",
            "total": 2,
            "entry": [
                {
                    "resource": {
                        "resourceType": "DocumentReference",
                        "id": "doc-001",
                        "status": "current"
                    }
                },
                {
                    "resource": {
                        "resourceType": "DocumentReference",
                        "id": "doc-002",
                        "status": "current"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = scheduler.fetch_document_references()
        
        assert result is not None
        assert result["total"] == 2
        assert len(result["entry"]) == 2
        
        # Verify request
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "DocumentReference" in call_args[0][0]
        assert call_args[1]['headers']['Authorization'] == 'Bearer test_access_token'
    
    def test_fetch_document_references_no_token(self, scheduler, caplog):
        """Test fetching when no token available."""
        scheduler.auth_client.get_token.return_value = None
        
        result = scheduler.fetch_document_references()
        
        assert result is None
        assert "No access token could be retrieved" in caplog.text
    
    @patch('documentrefscheduler.EsmdDocumentRefLettersPullScheduler.requests.get')
    def test_fetch_document_references_http_error(self, mock_get, scheduler, caplog):
        """Test fetching with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        result = scheduler.fetch_document_references()
        
        assert result is None
        assert "HTTP error" in caplog.text
    
    def test_schedule_pull_job(self, scheduler):
        """Test scheduling pull job."""
        with patch.object(scheduler, 'fetch_document_references') as mock_fetch:
            mock_fetch.return_value = {"total": 1, "entry": []}
            
            result = scheduler.schedule_pull_job()
            
            mock_fetch.assert_called_once()
            assert result is not None
    
    def test_process_scheduled_documents(self, scheduler):
        """Test processing scheduled documents."""
        sample_bundle = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "DocumentReference",
                        "id": "doc-001",
                        "status": "current"
                    }
                }
            ]
        }
        
        with patch('documentrefscheduler.EsmdDocumentRefLettersPullScheduler.FhirDocumentReferenceDataProcessor') as mock_processor:
            mock_processor_instance = Mock()
            mock_processor.return_value = mock_processor_instance
            
            scheduler.process_scheduled_documents(sample_bundle)
            
            mock_processor.assert_called_once()
            mock_processor_instance.process_document_bundle.assert_called_once()


class TestFhirDocumentReferenceDataProcessor:
    """Test cases for FhirDocumentReferenceDataProcessor class."""
    
    @pytest.fixture
    def sample_document_bundle(self):
        """Sample document reference bundle."""
        return {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "DocumentReference",
                        "id": "doc-001",
                        "status": "current",
                        "content": [
                            {
                                "attachment": {
                                    "url": "Binary/binary-001",
                                    "contentType": "application/pdf",
                                    "title": "Test Document"
                                }
                            }
                        ]
                    }
                }
            ]
        }
    
    def test_init(self, sample_document_bundle):
        """Test FhirDocumentReferenceDataProcessor initialization."""
        processor = FhirDocumentReferenceDataProcessor(sample_document_bundle)
        
        assert processor.document_bundle == sample_document_bundle
        assert processor.logger is not None
    
    def test_process_document_bundle(self, sample_document_bundle):
        """Test processing document bundle."""
        processor = FhirDocumentReferenceDataProcessor(sample_document_bundle)
        
        with patch.object(processor, 'extract_binary_references') as mock_extract, \
             patch.object(processor, 'download_binary_files') as mock_download:
            
            mock_extract.return_value = ["Binary/binary-001"]
            mock_download.return_value = True
            
            result = processor.process_document_bundle()
            
            mock_extract.assert_called_once()
            mock_download.assert_called_once_with(["Binary/binary-001"])
            assert result is True
    
    def test_extract_binary_references(self, sample_document_bundle):
        """Test extracting binary references."""
        processor = FhirDocumentReferenceDataProcessor(sample_document_bundle)
        
        binary_refs = processor.extract_binary_references()
        
        assert len(binary_refs) == 1
        assert "Binary/binary-001" in binary_refs
    
    def test_extract_binary_references_no_content(self):
        """Test extracting binary references when no content."""
        empty_bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "DocumentReference",
                        "id": "doc-001",
                        "status": "current"
                        # No content section
                    }
                }
            ]
        }
        processor = FhirDocumentReferenceDataProcessor(empty_bundle)
        
        binary_refs = processor.extract_binary_references()
        
        assert len(binary_refs) == 0
    
    def test_download_binary_files(self, sample_document_bundle):
        """Test downloading binary files."""
        processor = FhirDocumentReferenceDataProcessor(sample_document_bundle)
        
        with patch('documentrefscheduler.EsmdFhirDocumentReferenceDataProcessor.BinaryFileExtractor') as mock_extractor:
            mock_extractor_instance = Mock()
            mock_extractor_instance.download_binary.return_value = True
            mock_extractor.return_value = mock_extractor_instance
            
            result = processor.download_binary_files(["Binary/binary-001"])
            
            assert result is True
            mock_extractor_instance.download_binary.assert_called_once()
    
    def test_validate_document_references(self, sample_document_bundle):
        """Test validating document references."""
        processor = FhirDocumentReferenceDataProcessor(sample_document_bundle)
        
        is_valid, errors = processor.validate_document_references()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_document_references_invalid(self):
        """Test validating invalid document references."""
        invalid_bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "DocumentReference"
                        # Missing required fields
                    }
                }
            ]
        }
        processor = FhirDocumentReferenceDataProcessor(invalid_bundle)
        
        is_valid, errors = processor.validate_document_references()
        
        assert is_valid is False
        assert len(errors) > 0


class TestFindDocRefUtility:
    """Test cases for FindDocRefUtility class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies."""
        with patch('documentrefscheduler.EsmdFindDocRefUtility.EsmdAuthClient') as mock_auth, \
             patch('documentrefscheduler.EsmdFindDocRefUtility.ConfigUtility') as mock_config:
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_token"
            mock_auth.return_value = mock_auth_instance
            
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config.return_value = mock_config_instance
            
            yield {'auth': mock_auth_instance, 'config': mock_config_instance}
    
    @pytest.fixture
    def find_utility(self, mock_dependencies):
        """Create FindDocRefUtility instance."""
        return FindDocRefUtility()
    
    @patch('documentrefscheduler.EsmdFindDocRefUtility.requests.get')
    def test_find_documents_by_date_range(self, mock_get, find_utility):
        """Test finding documents by date range."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Bundle",
            "total": 1,
            "entry": [
                {
                    "resource": {
                        "resourceType": "DocumentReference",
                        "id": "doc-001"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        result = find_utility.find_documents_by_date_range(start_date, end_date)
        
        assert result is not None
        assert result["total"] == 1
        
        # Verify query parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "date" in call_args[1]["params"]
    
    def test_find_documents_by_patient_id(self, find_utility):
        """Test finding documents by patient ID."""
        with patch('documentrefscheduler.EsmdFindDocRefUtility.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"resourceType": "Bundle", "total": 0}
            mock_get.return_value = mock_response
            
            result = find_utility.find_documents_by_patient_id("patient-123")
            
            assert result is not None
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "patient-123" in str(call_args[1]["params"])
    
    def test_find_documents_by_status(self, find_utility):
        """Test finding documents by status."""
        with patch('documentrefscheduler.EsmdFindDocRefUtility.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"resourceType": "Bundle", "total": 0}
            mock_get.return_value = mock_response
            
            result = find_utility.find_documents_by_status("current")
            
            assert result is not None
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "current" in str(call_args[1]["params"])


class TestBinaryFileExtractor:
    """Test cases for BinaryFileExtractor class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies."""
        with patch('documentrefscheduler.EsmdBinaryFileExtractor.EsmdAuthClient') as mock_auth, \
             patch('documentrefscheduler.EsmdBinaryFileExtractor.ConfigUtility') as mock_config:
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_token"
            mock_auth.return_value = mock_auth_instance
            
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config.return_value = mock_config_instance
            
            yield {'auth': mock_auth_instance, 'config': mock_config_instance}
    
    @pytest.fixture
    def extractor(self, mock_dependencies):
        """Create BinaryFileExtractor instance."""
        return BinaryFileExtractor()
    
    @patch('documentrefscheduler.EsmdBinaryFileExtractor.requests.get')
    def test_download_binary_success(self, mock_get, extractor, tmp_path):
        """Test successful binary file download."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"Binary file content"
        mock_response.headers = {'content-type': 'application/pdf'}
        mock_get.return_value = mock_response
        
        output_path = tmp_path / "downloaded_file.pdf"
        
        result = extractor.download_binary("Binary/binary-001", str(output_path))
        
        assert result is True
        assert output_path.exists()
        assert output_path.read_bytes() == b"Binary file content"
    
    def test_download_binary_no_token(self, extractor, caplog):
        """Test binary download without token."""
        extractor.auth_client.get_token.return_value = None
        
        result = extractor.download_binary("Binary/binary-001", "/tmp/test.pdf")
        
        assert result is False
        assert "No access token" in caplog.text
    
    @patch('documentrefscheduler.EsmdBinaryFileExtractor.requests.get')
    def test_download_binary_http_error(self, mock_get, extractor, caplog):
        """Test binary download with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        result = extractor.download_binary("Binary/not-found", "/tmp/test.pdf")
        
        assert result is False
        assert "HTTP error" in caplog.text
    
    def test_get_binary_metadata(self, extractor):
        """Test getting binary metadata."""
        with patch('documentrefscheduler.EsmdBinaryFileExtractor.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "resourceType": "Binary",
                "id": "binary-001",
                "contentType": "application/pdf",
                "securityContext": {
                    "reference": "DocumentReference/doc-001"
                }
            }
            mock_get.return_value = mock_response
            
            metadata = extractor.get_binary_metadata("Binary/binary-001")
            
            assert metadata is not None
            assert metadata["contentType"] == "application/pdf"


class TestTransactionNotificationScheduler:
    """Test cases for TransactionNotificationScheduler class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies."""
        with patch('notificationscheduler.EsmdTransactionNotificationScheduler.setup_logger') as mock_logger, \
             patch('notificationscheduler.EsmdTransactionNotificationScheduler.ConfigUtility') as mock_config, \
             patch('notificationscheduler.EsmdTransactionNotificationScheduler.EsmdAuthClient') as mock_auth:
            
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config.return_value = mock_config_instance
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_access_token"
            mock_auth.return_value = mock_auth_instance
            
            yield {
                'logger': mock_logger,
                'config': mock_config_instance,
                'auth': mock_auth_instance
            }
    
    @pytest.fixture
    def scheduler(self, mock_dependencies):
        """Create TransactionNotificationScheduler instance."""
        return TransactionNotificationScheduler()
    
    def test_init(self, scheduler, mock_dependencies):
        """Test TransactionNotificationScheduler initialization."""
        assert scheduler.base_url == "http://test-server:9012/fhir"
        assert scheduler.config_util is not None
        assert scheduler.auth_client is not None
    
    def test_schedule_notification_check(self, scheduler):
        """Test scheduling notification check."""
        with patch.object(scheduler, 'check_pending_notifications') as mock_check:
            mock_check.return_value = True
            
            result = scheduler.schedule_notification_check()
            
            mock_check.assert_called_once()
            assert result is True
    
    @patch('notificationscheduler.EsmdTransactionNotificationScheduler.requests.get')
    def test_check_pending_notifications(self, mock_get, scheduler):
        """Test checking pending notifications."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Bundle",
            "total": 1,
            "entry": [
                {
                    "resource": {
                        "resourceType": "Task",
                        "id": "notification-001",
                        "status": "ready"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = scheduler.check_pending_notifications()
        
        assert result is not None
        assert result["total"] == 1
        mock_get.assert_called_once()
    
    def test_process_notification_tasks(self, scheduler):
        """Test processing notification tasks."""
        sample_tasks = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "Task",
                        "id": "task-001",
                        "status": "ready"
                    }
                }
            ]
        }
        
        with patch.object(scheduler, 'send_notification') as mock_send:
            mock_send.return_value = True
            
            result = scheduler.process_notification_tasks(sample_tasks)
            
            mock_send.assert_called_once()
            assert result is True
    
    def test_send_notification(self, scheduler):
        """Test sending notification."""
        task_data = {
            "resourceType": "Task",
            "id": "task-001",
            "status": "ready",
            "input": [
                {
                    "type": {
                        "coding": [
                            {"code": "notification-endpoint"}
                        ]
                    },
                    "valueString": "http://example.com/webhook"
                }
            ]
        }
        
        with patch('notificationscheduler.EsmdTransactionNotificationScheduler.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            result = scheduler.send_notification(task_data)
            
            assert result is True
            mock_post.assert_called_once()


class TestFindListTransNotificationUtility:
    """Test cases for FindListTransNotificationUtility class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies."""
        with patch('notificationscheduler.EsmdFindListTransNotificationUtility.EsmdAuthClient') as mock_auth, \
             patch('notificationscheduler.EsmdFindListTransNotificationUtility.ConfigUtility') as mock_config:
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_token"
            mock_auth.return_value = mock_auth_instance
            
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config.return_value = mock_config_instance
            
            yield {'auth': mock_auth_instance, 'config': mock_config_instance}
    
    @pytest.fixture
    def find_utility(self, mock_dependencies):
        """Create FindListTransNotificationUtility instance."""
        return FindListTransNotificationUtility()
    
    @patch('notificationscheduler.EsmdFindListTransNotificationUtility.requests.get')
    def test_find_pending_notifications(self, mock_get, find_utility):
        """Test finding pending notifications."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "Bundle",
            "total": 1,
            "entry": [
                {
                    "resource": {
                        "resourceType": "Task",
                        "id": "notification-001",
                        "status": "ready"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = find_utility.find_pending_notifications()
        
        assert result is not None
        assert result["total"] == 1
        mock_get.assert_called_once()
    
    def test_find_notifications_by_transaction_id(self, find_utility):
        """Test finding notifications by transaction ID."""
        with patch('notificationscheduler.EsmdFindListTransNotificationUtility.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"resourceType": "Bundle", "total": 0}
            mock_get.return_value = mock_response
            
            result = find_utility.find_notifications_by_transaction_id("TXN-123")
            
            assert result is not None
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "TXN-123" in str(call_args[1]["params"])
    
    def test_find_failed_notifications(self, find_utility):
        """Test finding failed notifications."""
        with patch('notificationscheduler.EsmdFindListTransNotificationUtility.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "resourceType": "Bundle",
                "total": 1,
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Task",
                            "id": "failed-001",
                            "status": "failed"
                        }
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            result = find_utility.find_failed_notifications()
            
            assert result is not None
            assert result["total"] == 1
            mock_get.assert_called_once()


@pytest.mark.integration
class TestSchedulerModulesIntegration:
    """Integration tests for scheduler modules."""
    
    def test_document_processing_workflow(self):
        """Test complete document processing workflow."""
        # Mock document bundle
        document_bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "DocumentReference",
                        "id": "doc-integration-001",
                        "status": "current",
                        "content": [
                            {
                                "attachment": {
                                    "url": "Binary/binary-integration-001",
                                    "contentType": "application/pdf"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        # Test document processor
        processor = FhirDocumentReferenceDataProcessor(document_bundle)
        binary_refs = processor.extract_binary_references()
        assert len(binary_refs) == 1
        
        # Test validation
        is_valid, errors = processor.validate_document_references()
        assert is_valid is True
    
    def test_notification_workflow(self):
        """Test complete notification workflow."""
        # Mock notification tasks
        notification_tasks = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "Task",
                        "id": "notification-integration-001",
                        "status": "ready",
                        "input": [
                            {
                                "type": {
                                    "coding": [
                                        {"code": "notification-endpoint"}
                                    ]
                                },
                                "valueString": "http://example.com/webhook"
                            }
                        ]
                    }
                }
            ]
        }
        
        # Test notification scheduler
        with patch('notificationscheduler.EsmdTransactionNotificationScheduler.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            scheduler = TransactionNotificationScheduler()
            result = scheduler.process_notification_tasks(notification_tasks)
            
            assert result is True
            mock_post.assert_called_once()
    
    def test_end_to_end_scheduler_integration(self):
        """Test end-to-end scheduler integration."""
        # Test document reference scheduler
        with patch('documentrefscheduler.EsmdDocumentRefLettersPullScheduler.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "resourceType": "Bundle",
                "total": 1,
                "entry": [
                    {
                        "resource": {
                            "resourceType": "DocumentReference",
                            "id": "integration-doc-001"
                        }
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            doc_scheduler = DocumentRefLettersPullScheduler()
            doc_result = doc_scheduler.fetch_document_references()
            assert doc_result["total"] == 1
        
        # Test notification scheduler
        with patch('notificationscheduler.EsmdTransactionNotificationScheduler.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "resourceType": "Bundle",
                "total": 1,
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Task",
                            "id": "integration-task-001"
                        }
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            notification_scheduler = TransactionNotificationScheduler()
            notification_result = notification_scheduler.check_pending_notifications()
            assert notification_result["total"] == 1 