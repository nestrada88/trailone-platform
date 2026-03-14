
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class GPXProcessingError(ValueError):
    """Domain-specific exception for invalid GPX processing requests."""


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GPXProcessingError)
    async def handle_gpx_error(_: Request, exc: GPXProcessingError) -> JSONResponse:
        return JSONResponse(status_code=400, content={'detail': str(exc)})

    @app.exception_handler(ValueError)
    async def handle_value_error(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={'detail': str(exc)})
