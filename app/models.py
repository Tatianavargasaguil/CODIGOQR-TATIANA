from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .db import Base

# Bogotá timezone for defaults
bogota_tz = ZoneInfo("America/Bogota")

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    # campos adicionales solicitados por el usuario
    origen = Column(String, nullable=True)
    destino = Column(String, nullable=True)
    responsable_origen = Column(String, nullable=True)
    responsable_destino = Column(String, nullable=True)
    nivel_gasolina = Column(Float, nullable=True)
    kilometraje = Column(Float, nullable=True)
    observaciones = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=bogota_tz))

    locations = relationship("Location", back_populates="vehicle")


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=bogota_tz))

    vehicle = relationship("Vehicle", back_populates="locations")