from sqlalchemy import desc, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(self, filename: str, content_hash: str) -> Job:
        job = Job(
            filename=filename,
            content_hash=content_hash,
            status="pending",
            progress=0,
            total_chunks=0,
            processed_chunks=0,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_job(self, job_id: int) -> Job | None:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def get_latest_by_content_hash(self, content_hash: str) -> Job | None:
        result = await self.db.execute(
            select(Job)
            .where(Job.content_hash == content_hash)
            .order_by(desc(Job.id))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: int,
        status: str,
        progress: int | None = None,
        document_id: int | None = None,
        error_message: str | None = None,
    ) -> None:
        job = await self.get_job(job_id)
        if job:
            job.status = status
            if progress is not None:
                job.progress = progress
            if document_id is not None:
                job.document_id = document_id
            if error_message is not None:
                job.error_message = error_message

    async def delete_jobs_by_document_id(self, document_id: int) -> None:
        await self.db.execute(
            delete(Job).where(Job.document_id == document_id)
        )
        await self.db.flush()
