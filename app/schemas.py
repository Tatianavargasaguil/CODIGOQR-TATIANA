from pydantic import BaseModel
from typing import Optional


class LocationCreate(BaseModel):
    latitude: float
    longitude: float


class VehicleCreate(BaseModel):
    code: str
    name: str
    origen: Optional[str] = None
    destino: Optional[str] = None
    responsable_origen: Optional[str] = None
    responsable_destino: Optional[str] = None
    nivel_gasolina: Optional[float] = None
    kilometraje: Optional[float] = None
    observaciones: Optional[str] = None


class VehicleResponse(BaseModel):
    id: int
    code: str
    name: str
    origen: Optional[str] = None
    destino: Optional[str] = None
    responsable_origen: Optional[str] = None
    responsable_destino: Optional[str] = None
    nivel_gasolina: Optional[float] = None
    kilometraje: Optional[float] = None
    observaciones: Optional[str] = None
    
    class Config:
        from_attributes = True