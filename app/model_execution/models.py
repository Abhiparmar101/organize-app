from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Database setup
DATABASE_URL = "sqlite:///crowd_count.db"  # You can change this to a different database URL if needed
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define the CrowdCount model
class CrowdCount(Base):
    __tablename__ = 'crowd_count'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    stream_name = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    image_name = Column(String, nullable=False)
    camera_id = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    num_people = Column(Integer, nullable=False)

# Create the table if it does not exist
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
