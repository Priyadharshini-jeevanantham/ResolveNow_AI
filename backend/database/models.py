from sqlalchemy.orm import declarative_base
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import JSON

Base = declarative_base()

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)

    ticket_id = Column(String, unique=True)

    topic = Column(String)

    description = Column(Text)

    priority = Column(String)

    status = Column(String)

    created_by = Column(String)

    user_email = Column(String)

    assigned_to = Column(String)

    assigned_group = Column(String)

    created_time = Column(String)

    ai_result = Column(JSON)