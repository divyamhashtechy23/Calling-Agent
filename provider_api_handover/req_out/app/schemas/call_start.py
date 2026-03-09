from pydantic import BaseModel, ConfigDict, Field

class CallStartRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    orgId: str
    userId: str
    sequenceId: str
    leadId: str

    leadName: str
    leadPhone: str
    leadCompany: str | None = None

    language: str = Field(..., description="en | hi | gu")
    callPurpose: str
    callingScript: str

    # Backward-compatible: accepts both callerName/orgName and caller_name/org_name
    callerName: str = Field(validation_alias="caller_name")
    orgName: str = Field(validation_alias="org_name")
