from pydantic import BaseModel, field_validator
from typing import Optional, Union


class LocationCreate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # Agregar campos de formulario a LocationCreate
    origen: Optional[str] = None
    destino: Optional[str] = None
    responsable_origen: Optional[str] = None
    responsable_destino: Optional[str] = None
    nivel_gasolina: Optional[str] = None
    kilometraje: Optional[str] = None
    observaciones: Optional[str] = None
    direccion_completa: Optional[str] = None


class VehicleCreate(BaseModel):
    code: str
    name: str


class VehicleResponse(BaseModel):
    id: int
    code: str
    name: str
    
    class Config:
        from_attributes = True


class UnscannedVehicleCreate(BaseModel):
    responsable_esperado: Optional[str] = None
    motivo: Optional[str] = None