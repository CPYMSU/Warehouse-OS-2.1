from fastapi import APIRouter, Depends

from app.api.deps import ActorContext, current_actor
from app.api.router import industry_templates

router = APIRouter(tags=["full-stack-overrides"])


@router.get("/api/platform/templates")
def platform_templates_stable(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return industry_templates(actor)
