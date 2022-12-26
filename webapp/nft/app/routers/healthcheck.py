from fastapi import APIRouter

from nft.app.schemas import HealthStatusResponse

router = APIRouter(prefix='/health',
                   tags=['healthcheck'])


@router.get('',
            summary='Get app health status',
            description='Returns health status',
            response_model=HealthStatusResponse)
async def get_healthcheck():
    return {'healthy': True}
