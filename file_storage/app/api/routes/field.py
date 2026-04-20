from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_field_service
from app.schemas.dto import CreateFieldRequest, CreateFieldResponse, FieldResponse
from app.services.field import FieldService

router = APIRouter(prefix="/field", tags=["field"])


@router.post("/", response_model=CreateFieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(
    request: CreateFieldRequest,
    service: FieldService = Depends(get_field_service),
) -> CreateFieldResponse:
    return CreateFieldResponse(id=service.create(request.name, request.description))


@router.get("/s/{field_id}", response_model=FieldResponse)
def get_field_by_id(field_id: UUID, service: FieldService = Depends(get_field_service)) -> FieldResponse:
    return FieldResponse(**service.get_by_id(field_id))


@router.patch("/s/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_field_by_id(
    field_id: UUID,
    values: dict[str, object],
    service: FieldService = Depends(get_field_service),
) -> Response:
    service.update_by_id(field_id, values)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/s/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field_by_id(field_id: UUID, service: FieldService = Depends(get_field_service)) -> Response:
    service.delete_by_id(field_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/", response_model=list[FieldResponse])
def get_all_fields(service: FieldService = Depends(get_field_service)) -> list[FieldResponse]:
    return [FieldResponse(**item) for item in service.get_all()]


