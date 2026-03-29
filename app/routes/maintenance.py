from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import date, datetime
from pydantic import BaseModel

from ..core.db import get_db
from ..models.maintenance import MaintenanceServiceType, MaintenanceService
from ..models.vehicle import Vehicle
from ..models.vehicle_history import VehicleHistory
from ..routes.auth import get_current_admin


def _add_service_history(
    db: Session,
    vehicle_id: int,
    action_type: str,
    description: str,
    changed_by_id: int | None = None,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    """Write a VehicleHistory entry for a maintenance service event."""
    entry = VehicleHistory(
        vehicle_id=vehicle_id,
        changed_by_id=changed_by_id,
        changed_at=datetime.now(),
        action_type=action_type,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        description=description,
    )
    db.add(entry)
    db.flush()

router = APIRouter(prefix="/admin/maintenance", tags=["maintenance"])


# === Pydantic Models ===

class ServiceTypeCreate(BaseModel):
    name: str
    description: str | None = None
    average_time_hours: float | None = None
    default_price: float | None = None
    active: bool = True


class ServiceTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    average_time_hours: float | None = None
    default_price: float | None = None
    active: bool | None = None


class ServiceCreate(BaseModel):
    vehicle_id: int
    service_type_id: int
    admin_id: int | None = None
    pickup_date: str | None = None
    dropoff_date: str | None = None
    location: str | None = None
    notes: str | None = None
    status: str = "Programmed"
    cost: float | None = None
    mileage: int | None = None


class ServiceUpdate(BaseModel):
    vehicle_id: int | None = None
    service_type_id: int | None = None
    admin_id: int | None = None
    pickup_date: str | None = None
    dropoff_date: str | None = None
    location: str | None = None
    notes: str | None = None
    status: str | None = None
    cost: float | None = None
    mileage: int | None = None


# === Service Types Routes ===

@router.get("/service-types")
async def get_service_types(
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get all maintenance service types"""
    service_types = db.query(MaintenanceServiceType).order_by(MaintenanceServiceType.name).all()
    return service_types


@router.get("/service-types/{type_id}")
async def get_service_type(
    type_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get a specific service type"""
    service_type = db.query(MaintenanceServiceType).filter(MaintenanceServiceType.id == type_id).first()
    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")
    return service_type


@router.post("/service-types")
async def create_service_type(
    data: ServiceTypeCreate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Create a new service type"""
    service_type = MaintenanceServiceType(**data.model_dump())
    db.add(service_type)
    db.commit()
    db.refresh(service_type)
    return service_type


@router.put("/service-types/{type_id}")
async def update_service_type(
    type_id: int,
    data: ServiceTypeUpdate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Update a service type"""
    service_type = db.query(MaintenanceServiceType).filter(MaintenanceServiceType.id == type_id).first()
    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(service_type, key, value)
    
    db.commit()
    db.refresh(service_type)
    return service_type


@router.delete("/service-types/{type_id}")
async def delete_service_type(
    type_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Delete a service type"""
    service_type = db.query(MaintenanceServiceType).filter(MaintenanceServiceType.id == type_id).first()
    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")
    
    # Check if type is being used
    services_count = db.query(MaintenanceService).filter(MaintenanceService.service_type_id == type_id).count()
    if services_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete service type. It is used in {services_count} service record(s)."
        )
    
    db.delete(service_type)
    db.commit()
    return {"message": "Service type deleted successfully"}


# === Maintenance Services Routes ===

@router.get("/services")
async def get_services(
    vehicle_id: int | None = None,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get all maintenance services"""
    query = db.query(MaintenanceService).options(
        joinedload(MaintenanceService.vehicle),
        joinedload(MaintenanceService.service_type)
    )
    
    if vehicle_id:
        query = query.filter(MaintenanceService.vehicle_id == vehicle_id)
    
    services = query.order_by(MaintenanceService.pickup_date.desc()).all()
    
    # Manually convert to dict to include relationships
    result = []
    for service in services:
        service_dict = {
            "id": service.id,
            "vehicle_id": service.vehicle_id,
            "service_type_id": service.service_type_id,
            "admin_id": service.admin_id,
            "pickup_date": service.pickup_date,
            "dropoff_date": service.dropoff_date,
            "location": service.location,
            "mileage": service.mileage,
            "cost": float(service.cost) if service.cost is not None else None,
            "notes": service.notes,
            "status": service.status,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "admin": {
                "id": service.admin.id,
                "name": service.admin.full_name,
                "email": service.admin.email
            } if service.admin else None,
            "vehicle": {
                "id": service.vehicle.id,
                "make": service.vehicle.make,
                "model": service.vehicle.model,
                "brand_name": service.vehicle.brand_name,
                "model_name": service.vehicle.model_name,
                "license_plate": service.vehicle.license_plate,
                "vehicle_class": getattr(service.vehicle, 'vehicle_class', None)
            } if service.vehicle else None,
            "service_type": {
                "id": service.service_type.id,
                "name": service.service_type.name,
                "description": service.service_type.description,
                "default_price": float(service.service_type.default_price) if service.service_type.default_price is not None else None
            } if service.service_type else None
        }
        result.append(service_dict)
    
    return result


@router.get("/services/{service_id}")
async def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get a specific maintenance service"""
    service = db.query(MaintenanceService).options(
        joinedload(MaintenanceService.vehicle),
        joinedload(MaintenanceService.service_type)
    ).filter(MaintenanceService.id == service_id).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return service


@router.post("/services")
async def create_service(
    data: ServiceCreate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Create a new maintenance service"""
    # Verify vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Verify service type exists
    service_type = db.query(MaintenanceServiceType).filter(MaintenanceServiceType.id == data.service_type_id).first()
    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")
    
    service = MaintenanceService(**data.model_dump())
    db.add(service)
    db.flush()  # get service.id without closing the transaction

    date_info = f" on {data.pickup_date}" if data.pickup_date else ""
    location_info = f" at {data.location}" if data.location else ""
    _add_service_history(
        db=db,
        vehicle_id=data.vehicle_id,
        action_type="SERVICE_PLANNED",
        description=f"Service planned: {service_type.name}{date_info}{location_info}",
        changed_by_id=getattr(admin, 'id', None),
        field_name="maintenance",
        new_value=service_type.name,
    )
    db.commit()
    db.refresh(service)
    return service


@router.put("/services/{service_id}")
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Update a maintenance service"""
    service = db.query(MaintenanceService).options(
        joinedload(MaintenanceService.service_type)
    ).filter(MaintenanceService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    updates = data.model_dump(exclude_unset=True)
    old_status = service.status

    for key, value in updates.items():
        setattr(service, key, value)

    service_type_name = service.service_type.name if service.service_type else f"Service #{service_id}"
    new_status = service.status

    if old_status != new_status:
        _add_service_history(
            db=db,
            vehicle_id=service.vehicle_id,
            action_type="SERVICE_STATUS_CHANGED",
            description=f"Service '{service_type_name}' status changed from {old_status} to {new_status}",
            changed_by_id=getattr(admin, 'id', None),
            field_name="service_status",
            old_value=old_status,
            new_value=new_status,
        )
    else:
        _add_service_history(
            db=db,
            vehicle_id=service.vehicle_id,
            action_type="SERVICE_UPDATED",
            description=f"Service '{service_type_name}' updated",
            changed_by_id=getattr(admin, 'id', None),
            field_name="maintenance",
        )

    db.commit()
    db.refresh(service)
    return service


@router.patch("/services/{service_id}")
async def patch_service(
    service_id: int,
    data: ServiceUpdate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Partially update a maintenance service"""
    service = db.query(MaintenanceService).options(
        joinedload(MaintenanceService.service_type)
    ).filter(MaintenanceService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    updates = data.model_dump(exclude_unset=True)
    old_status = service.status

    for key, value in updates.items():
        setattr(service, key, value)

    service_type_name = service.service_type.name if service.service_type else f"Service #{service_id}"
    new_status = service.status

    if old_status != new_status:
        _add_service_history(
            db=db,
            vehicle_id=service.vehicle_id,
            action_type="SERVICE_STATUS_CHANGED",
            description=f"Service '{service_type_name}' status changed from {old_status} to {new_status}",
            changed_by_id=getattr(admin, 'id', None),
            field_name="service_status",
            old_value=old_status,
            new_value=new_status,
        )
    else:
        _add_service_history(
            db=db,
            vehicle_id=service.vehicle_id,
            action_type="SERVICE_UPDATED",
            description=f"Service '{service_type_name}' updated",
            changed_by_id=getattr(admin, 'id', None),
            field_name="maintenance",
        )

    db.commit()
    db.refresh(service)
    return service


@router.delete("/services/{service_id}")
async def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Delete a maintenance service"""
    service = db.query(MaintenanceService).options(
        joinedload(MaintenanceService.service_type)
    ).filter(MaintenanceService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    vehicle_id = service.vehicle_id
    service_type_name = service.service_type.name if service.service_type else f"Service #{service_id}"
    date_info = f" (planned: {service.pickup_date})" if service.pickup_date else ""

    _add_service_history(
        db=db,
        vehicle_id=vehicle_id,
        action_type="SERVICE_DELETED",
        description=f"Service deleted: {service_type_name}{date_info}",
        changed_by_id=getattr(admin, 'id', None),
        field_name="maintenance",
        old_value=service_type_name,
    )

    db.delete(service)
    db.commit()
    return {"message": "Service deleted successfully"}
