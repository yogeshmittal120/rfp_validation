from sqlalchemy import Column, Integer, String

from .database import Base


class RFP(Base):
    __tablename__ = "rfp"

    id = Column(Integer, primary_key=True, index=True)
    rfp_title = Column(String, nullable=False, default="Cisco Partner RFP")
    requirement = Column(String, nullable=False)
    cisco_partner_response = Column(String, nullable=False)
