from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Mock Pier API",
    description="Simula a API da Pier para consulta de veículos por placa.",
    version="1.0.0"
)

# Biblioteca pydantic para definir como serão estruturados os dados de entrada e saída da API

class Geolocalizacao(BaseModel):
    latitude: float
    longitude: float

class VehicleLookupRequest(BaseModel):
    license_plate: str
    geolocation: Geolocalizacao

class VehicleData(BaseModel):
    make: str
    model: str
    fabrication_year: int

class VehicleLookupResponse(BaseModel):
    vehicle_lookup_id: str | None
    vehicle: VehicleData | None
    status: str

# Dados mockados

veiculos_mock = {
    "MJF4A91": {
        "vehicle_lookup_id": "876543",
        "vehicle": {
            "make": "GM - Chevrolet",
            "model": "Celta ADVANTAGE",
            "fabrication_year": 2024
        },
        "status": "found"
    },
    "ABC1D23": {
        "vehicle_lookup_id": "999001",
        "vehicle": {
            "make": "Fiat",
            "model": "Pulse",
            "fabrication_year": 2022
        },
        "status": "found"
    }
}


@app.post(
    "/v1/inteli/vehicle-lookups",
    response_model=VehicleLookupResponse,
    summary="Consulta veículo por placa",
    description="Recebe uma placa e geolocalização, retorna os dados do veículo se encontrado."
)
async def vehicle_lookup(payload: VehicleLookupRequest):
    placa = payload.license_plate

    if placa in veiculos_mock:
        return veiculos_mock[placa]

    return {
        "vehicle_lookup_id": None,
        "vehicle": None,
        "status": "not_found"
    }