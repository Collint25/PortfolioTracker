"""HTMX response utilities."""

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response


def is_htmx_request(request: Request) -> bool:
    """Check if request is an HTMX request."""
    return request.headers.get("HX-Request") == "true"


def htmx_response(
    templates: Jinja2Templates,
    request: Request,
    full_template: str,
    partial_template: str,
    context: dict,
) -> Response:
    """
    Return appropriate template response based on HTMX vs full page request.

    Args:
        templates: Jinja2Templates instance
        request: FastAPI Request object
        full_template: Template name for full page loads
        partial_template: Template name for HTMX partial updates
        context: Template context dict (must not include 'request')

    Returns:
        TemplateResponse with appropriate template
    """
    template_name = partial_template if is_htmx_request(request) else full_template
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context,
    )
