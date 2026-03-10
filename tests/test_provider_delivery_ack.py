"""
Unit tests for ProviderDeliveryAck module.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from esmd_shared.auth import EsmdAuthClient
from esmd_shared.config import ConfigUtility
from esmd_shared.exceptions import AuthenticationError , NetworkError
from datetime import datetime, timedelta
from esmd_shared.models import ProviderDeliveryAckMetadata, TokenInfo
from providerdeliveryack.ProviderDeliveryAckMetadata import ProviderDeliveryAckMetadataHandler
from providerdeliveryack.EsmdProviderDeliveryAckRequestSubmitter import EsmdProviderDeliveryAckRequestSubmitter 
from providerdeliveryack.EsmdProviderDeliveryAckResponse import ProviderDeliveryAckResponseHandler


class TestProviderDeliveryAck:
    """Test cases for ProviderDeliveryAck module."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('providerdeliveryack.EsmdProviderDeliveryAckRequestSubmitter.ConfigUtility') as mock_config, \
             patch('providerdeliveryack.EsmdProviderDeliveryAckRequestSubmitter.EsmdAuthClient') as mock_auth:
             
            
            # Set up mock returns
            mock_config_instance = Mock()
            mock_config_instance.get_fhir_server_url.return_value = "http://test-server:9012/fhir"
            mock_config.return_value = mock_config_instance
            
            mock_auth_instance = Mock()
            mock_auth_instance.get_token.return_value = "test_access_token"
            mock_auth.return_value = mock_auth_instance
            
            yield {
                #'logger': mock_logger,
                'config': mock_config_instance,
                'auth': mock_auth_instance
            }

    @pytest.fixture
    def metadata(self):
        """Mock metadata for tests."""
        return ProviderDeliveryAckMetadata(
            transaction_id="tx-123",
            organization_id="org-456",
            npi="9876543210",
            delivery_datetime="2025-07-08T12:11:20.253-05:00",
            diagnostics="some diagnostics text"
        )

    def test_create_list(self, mock_dependencies: dict[str, Mock], metadata: ProviderDeliveryAckMetadata):
        """Test creating a list of ProviderDeliveryAckMetadata."""
       
        handler = ProviderDeliveryAckMetadataHandler(metadata)
        result = handler.create_list()
        print("Created FHIR LIST resource:", result)
        # Assert
        assert result is not None
        assert result.get("resourceType") == "List"
     # Extensions - transaction id, organization id, npi, delivery datetime
        exts = result.get("extension", [])
        tx_ext = next((e for e in exts if "Esmd-Ext-TransactionId" in e.get("url", "")), None)
        org_ext = next((e for e in exts if "Esmd-Ext-OrganizationId" in e.get("url", "")), None)
        npi_ext = next((e for e in exts if "Esmd-Ext-NPI" in e.get("url", "")), None)
        dt_ext = next((e for e in exts if "Esmd-Ext-DeliveryDateTime" in e.get("url", "")), None)

        assert tx_ext is not None and tx_ext.get("valueString") == metadata.transaction_id
        assert org_ext is not None and org_ext.get("valueString") == metadata.organization_id
        assert npi_ext is not None and npi_ext.get("valueString") == metadata.npi
        assert dt_ext is not None and dt_ext.get("valueDateTime") == metadata.delivery_datetime

    def test_submit_provider_delivery_ack_failure(self, mock_dependencies: dict[str, Mock], metadata: ProviderDeliveryAckMetadata):
        """Test failed submission of ProviderDeliveryAck."""
        handler = ProviderDeliveryAckMetadataHandler(metadata)
        fhir_list = handler.create_list()
        
        submitter = EsmdProviderDeliveryAckRequestSubmitter()
        
        # Mock the requests.post to simulate a successful response
        with patch('providerdeliveryack.EsmdProviderDeliveryAckRequestSubmitter.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"resourceType": "OperationOutcome", "issue": []}
            mock_response.status_code = 412
            mock_post.return_value = mock_response
            
            result, status_code = submitter.submit_provider_delivery_ack(fhir_list)
            print("Submission result:", result)
            
            # Assert
            assert status_code == 412
            assert result is not None
            assert result.get("resourceType") == "OperationOutcome"
    
    def test_submit_provider_delivery_ack_success(self, mock_dependencies: dict[str, Mock], metadata: ProviderDeliveryAckMetadata):
        """Test successful submission of ProviderDeliveryAck."""
        handler = ProviderDeliveryAckMetadataHandler(metadata)
        fhir_list = handler.create_list()
        
        submitter = EsmdProviderDeliveryAckRequestSubmitter()
        
        # Mock the requests.post to simulate a successful response
        with patch('providerdeliveryack.EsmdProviderDeliveryAckRequestSubmitter.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"resourceType": "List", "issue": []}
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            result, status_code = submitter.submit_provider_delivery_ack(fhir_list)
            print("Submission result:", result)
            
            # Assert
            assert status_code == 200
            assert result is not None
            assert result.get("resourceType") == "List"

    # Integration tests with API
    @pytest.mark.integration    
    class TestProviderDeliveryAckIntegration:
        @pytest.fixture
        def metadata(self):
            """Mock metadata for tests."""
            return ProviderDeliveryAckMetadata(
            transaction_id="tx-123",
            organization_id="org-456",
            npi="9876543210",
            delivery_datetime="2025-07-08T12:11:20.253-05:00",
            diagnostics="some diagnostics text",
            severity="error",
            code="processing"
        )

        def test_submit_provider_delivery_ack_integration_failure(self,  metadata):
            """Test failed submission of ProviderDeliveryAck."""
            handler = ProviderDeliveryAckMetadataHandler(metadata)
            fhir_list = handler.create_list()

            submitter = EsmdProviderDeliveryAckRequestSubmitter()

            result, status_code = submitter.submit_provider_delivery_ack(fhir_list)
            print("Submission result:", result)

            # Assert
            assert status_code == 412
            assert result is not None
            assert result.get("resourceType") == "OperationOutcome"

        def test_submit_provider_delivery_ack_success_with_actual_data(self):
            """Test successful submission of ProviderDeliveryAck with actual data. Change this test data to use real data."""
            
            metadata = ProviderDeliveryAckMetadata(
            transaction_id="SAR0007320223EC",
            organization_id="urn:oid:123.456.657.127",
            npi="1568425007",
            delivery_datetime="2026-02-03T12:11:20.253-05:00"
        )
            handler = ProviderDeliveryAckMetadataHandler(metadata)
            fhir_list = handler.create_list()        
        
            submitter = EsmdProviderDeliveryAckRequestSubmitter()

            result, status_code = submitter.submit_provider_delivery_ack(fhir_list)
            print("Submission result:", result)

            # Assert
            assert status_code == 422
            assert result is not None
            assert result.get("resourceType") == "OperationOutcome"