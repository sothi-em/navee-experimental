"""Global skills management: list, update, delete, and clear (TinyDB)."""

from fastapi import APIRouter, HTTPException

from app.agent.memory import SkillStore
from app.core.models import Skill, SkillUpdate

router = APIRouter(prefix="/api/skills", tags=["skills"])


def _to_model(doc: dict) -> Skill:
    return Skill(
        id=doc["doc_id"],
        name=doc["name"],
        description=doc.get("description") or "",
        content=doc.get("content") or "",
        created_at=doc.get("created_at"),
    )


@router.get("", response_model=list[Skill])
def list_skills() -> list[Skill]:
    return [_to_model(s) for s in SkillStore().list_skills()]


@router.patch("/{skill_id}", response_model=Skill)
def update_skill(skill_id: int, payload: SkillUpdate) -> Skill:
    store = SkillStore()
    if not store.update_skill(skill_id, payload.name, payload.description, payload.content):
        raise HTTPException(status_code=404, detail="skill not found")
    doc = store.get_skill(skill_id)
    assert doc is not None
    return _to_model(doc)


@router.delete("/{skill_id}")
def delete_skill(skill_id: int) -> dict:
    if not SkillStore().delete_skill(skill_id):
        raise HTTPException(status_code=404, detail="skill not found")
    return {"deleted": True}


@router.delete("")
def clear_skills() -> dict:
    return {"deleted": SkillStore().clear_skills()}
