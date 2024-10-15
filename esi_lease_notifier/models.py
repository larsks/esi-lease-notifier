from pydantic import BaseModel, Field


class EmailConfiguration(BaseModel):
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str


class LeaseNotifierConfiguration(BaseModel):
    email: EmailConfiguration


class ConfigurationFile(BaseModel):
    esi_lease_notifier: LeaseNotifierConfiguration = Field(
        ..., alias="esi-lease-notifier"
    )
