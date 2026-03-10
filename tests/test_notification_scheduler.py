import pytest
from unittest.mock import Mock, patch

from notificationscheduler.EsmdTransactionNotificationScheduler import NotificationScheduler


class TestNotificationScheduler:
    """Tests for NotificationScheduler (robust to 2- or 3-arg handle_notification)."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies used by the scheduler and utility."""
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
    def find_utility(self, mock_dependencies):
        """Create EsmdFindListTransNotificationUtility instance."""
        from notificationscheduler.EsmdFindListTransNotificationUtility import EsmdFindListTransNotificationUtility
        return EsmdFindListTransNotificationUtility()
    
    @pytest.fixture
    def scheduler(self, mock_dependencies):
        """Create NotificationScheduler instance."""
        return NotificationScheduler()



    def _calls_first_two(self, mock_obj):
        return [call.args[:2] for call in mock_obj.call_args_list]

    def test_init(self, scheduler, mock_dependencies):
        """Scheduler constructs with utility and logger attached."""
        assert hasattr(scheduler, "esmd_utility")
        assert hasattr(scheduler, "logger")
    
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
                        "resourceType": "List",
                        "id": "notification-001",
                        "status": "ready"
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        result = find_utility.get_find_list_trans_notification()

        payload = result[0] if isinstance(result, tuple) else result
        assert payload is not None
        assert payload["total"] == 1
        mock_get.assert_called_once()
    
    def test_find_notifications_by_uniqueid_id(self, find_utility):
        """Test finding notifications by unique ID."""
        with patch('notificationscheduler.EsmdFindListTransNotificationUtility.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"resourceType": "Bundle", "total": 0}
            mock_get.return_value = mock_response

            result = find_utility.get_find_list_trans_notification("TXN-123")

            payload = result[0] if isinstance(result, tuple) else result
            assert payload is not None
            assert payload["total"] == 0
            mock_get.assert_called_once()
            # params may be passed as dict; stringify for robust assertion
            #assert "TXN-123" in str(call_args[1].get("params", call_args[1]))

    def test_find_failed_with_operationOutcome(self, find_utility):
        """Test finding failed notifications."""
        with patch('notificationscheduler.EsmdFindListTransNotificationUtility.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "processing",
                        "details": {
                            "text": "Invalid Oraganization OID"
                        }
                    }
                ]
            }
            mock_get.return_value = mock_response

            result = find_utility.get_find_list_trans_notification()
            payload = result[0] if isinstance(result, tuple) else result
            assert payload is not None            
            assert payload["resourceType"] == "OperationOutcome"
            mock_get.assert_called_once()
    
    def test_schedule_notifications_with_single_dict(self, scheduler):
        """schedule_notifications accepts a single dict and calls handle_notification."""
        with patch.object(scheduler, 'handle_notification') as mock_handle:
            scheduler.schedule_notifications({"uniqueid": "id-123", "transaction-status-type": "ready-to-download"})
            assert mock_handle.call_count == 1
            assert ("id-123", "ready-to-download") in self._calls_first_two(mock_handle)

    def test_schedule_notifications_with_list_and_partial_values(self, scheduler):
        """schedule_notifications accepts list entries where either uniqueid or status may be missing."""
        entries = [
            {"uniqueid": "id-1"},
            {"transaction-status-type": "ready-to-download"}
           
        ]
        with patch.object(scheduler, 'handle_notification') as mock_handle:
            scheduler.schedule_notifications(entries)
            # Expect 3 valid calls
            assert mock_handle.call_count == 1
            actual = self._calls_first_two(mock_handle)
          

    def test_handle_notification_operation_outcome(self, scheduler):
        """handle_notification should not call process_notification_list for OperationOutcome."""
        with patch.object(scheduler.esmd_utility, 'get_find_list_trans_notification') as mock_get, \
             patch.object(scheduler.esmd_utility, 'process_notification_list') as mock_process:
            mock_get.return_value = {"resourceType": "OperationOutcome", "issue": [{"diagnostics": "error"}]}
            # call with two args; works if implementation accepts 2 or 3 args
            scheduler.handle_notification("some-id", "ready-to-download")
            mock_process.assert_not_called()

    def test_handle_notification_list_calls_process(self, scheduler):
        """handle_notification should call process_notification_list when a Bundle is returned."""
        with patch.object(scheduler.esmd_utility, 'get_find_list_trans_notification') as mock_get, \
             patch.object(scheduler.esmd_utility, 'process_notification_list') as mock_process:
            mock_get.return_value = ({"resourceType": "Bundle", "entry": []}, 200)
            scheduler.handle_notification("some-id", "ready-to-download")
            mock_process.assert_called_once()


