from providerdeliveryack.EsmdProviderDeliveryAckRequestSubmitter import EsmdProviderDeliveryAckRequestSubmitter
from esmd_shared.logger import setup_logger  # Import the shared logger setup function
from providerdeliveryack.ProviderDeliveryAckMetadata import ProviderDeliveryAckMetadataHandler  # Import the shared ProviderDeliveryAckMetadata model
from esmd_shared.models import ProviderDeliveryAckMetadata, OperationOutcome

class ProviderDeliveryAckResponseHandler:
    def __init__(self, submitter: EsmdProviderDeliveryAckRequestSubmitter = None):
        self.logger = setup_logger(self.__class__.__name__)
        self.submitter = submitter or EsmdProviderDeliveryAckRequestSubmitter()

    def handle_submit_and_verify(self, fhir_list) -> dict:
        """
        Call submit_provider_delivery_ack and verify result.
        Returns a structured dict:
         - success: bool
         - http_status: int (when available)
         - operation_outcome: dict (if failed and returned by server)
         - response / error otherwise
        """
        operationOutcome_obj = None
        mapped_issues = []
        result , http_status = self.submitter.submit_provider_delivery_ack(fhir_list)
        print("Submit Result:", result )
        print("HTTP Status:", http_status)

        if http_status == 200 or http_status == 201:
            self.logger.info("Submit succeeded (HTTP %s)", http_status)
            return {"success": True, "http_status": http_status, "response": result}

        else:
            # extract operation outcome if present
            if result:
                op =  result.get("resourceType", "").lower() == "operationoutcome"
                print("Is OperationOutcome:", op)
                
                if op:
                     # result might be a JSON string containing an OperationOutcome
                    if not result and isinstance(result, str):
                        print("Result is a string, attempting to parse as JSON.")
                        try:
                            import json
                            parsed = json.loads(result)
                            if isinstance(parsed, dict) and parsed.get("resourceType", "").lower() == "operationoutcome":
                                operationOutcome_obj = parsed
                                print("Parsed OperationOutcome from string:", operationOutcome_obj)
                        except Exception:
                            pass

                    if op:
                        issues = result.get("issue", [])
                        print("issues found:", issues)
                        if issues and isinstance(issues, list) and len(issues) > 0:
                            for issue in issues:
                                # build the item first, then append it (append does not accept keyword args)
                                try:
                                    # try to use the dataclass if available
                                    from esmd_shared.models import OperationOutcomeIssue
                                    item = OperationOutcomeIssue(
                                        severity=issue.get("severity"),
                                        code=issue.get("code"),
                                        diagnostics=issue.get("diagnostics")
                                    )
                                except Exception:
                                    # fallback to plain dict
                                    item = {
                                        "severity": issue.get("severity"),
                                        "code": issue.get("code"),
                                        "diagnostics": issue.get("diagnostics"),
                                        "details": issue.get("details")
                                    }
                                mapped_issues.append(item)
                            print("Mapped issues:", mapped_issues)

                    return {"success": False, "http_status": http_status, "operation_outcome": operationOutcome_obj, "operation_outcome_obj": mapped_issues}

                return {"success": False, "http_status": http_status, "operation_outcome": op}

        # error (network/config)
        self.logger.error("Submit error: %s", result.get("error"))
        return {"success": False, "error": result.get("error")}
    
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
    submitter = ProviderDeliveryAckResponseHandler()
    submitter.handle_submit_and_verify(fhir_list)
    print(submitter)