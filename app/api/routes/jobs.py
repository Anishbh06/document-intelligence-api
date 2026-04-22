from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.core.security import require_api_key
from app.db.session import get_db
from app.repositories.job_repo import JobRepository
from app.schemas.job import JobResponse

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: int,
    _: None = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    repo = JobRepository(db)
    job = await repo.get_job(job_id)

    if not job:
        raise APIError(status_code=404, code="job_not_found", message="Job not found")

    return job
