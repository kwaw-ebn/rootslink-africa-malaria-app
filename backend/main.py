import os
from datetime import date as DateType, datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Text, Date, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rootslink_dev.db")

# Render/Postgres sometimes provides postgres://; SQLAlchemy expects postgresql+psycopg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Outreach(Base):
    __tablename__ = "outreaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[DateType] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    institution: Mapped[str] = mapped_column(String(180), nullable=False)
    male: Mapped[int] = mapped_column(Integer, default=0)
    female: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    knowledge: Mapped[int] = mapped_column(Integer, default=0)
    itn: Mapped[int] = mapped_column(Integer, default=0)
    myth: Mapped[str] = mapped_column(String(30), default="none")
    test: Mapped[str] = mapped_column(String(30), default="good")
    notes: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="Low")
    score: Mapped[int] = mapped_column(Integer, default=0)
    reasons_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Rootslink Africa Malaria Outreach API",
    version="1.0.0",
    description="Prototype backend for non-identifying malaria outreach program monitoring."
)

origins_env = os.getenv("CORS_ORIGINS", "*")
origins = ["*"] if origins_env.strip() == "*" else [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def priority_score(knowledge: int, itn: int, myth: str, test: str):
    score = 0
    reasons = []

    if knowledge < 50:
        score += 35
        reasons.append("knowledge score is below 50%")
    elif knowledge < 70:
        score += 20
        reasons.append("knowledge is moderate and needs reinforcement")

    if itn < 50:
        score += 30
        reasons.append("reported ITN use is below 50%")
    elif itn < 70:
        score += 15
        reasons.append("ITN use is moderate")

    if myth == "strong":
        score += 25
        reasons.append("strong harmful malaria beliefs were reported")
    elif myth == "some":
        score += 12
        reasons.append("some misconceptions remain")

    if test == "poor":
        score += 25
        reasons.append("treatment without testing is common")
    elif test == "mixed":
        score += 12
        reasons.append("testing practice is inconsistent")

    score = min(score, 100)
    priority = "High" if score >= 55 else "Medium" if score >= 25 else "Low"
    return score, priority, reasons


class OutreachCreate(BaseModel):
    date: DateType
    type: str = Field(min_length=1, max_length=80)
    institution: str = Field(min_length=1, max_length=180)
    male: int = Field(ge=0, le=100000)
    female: int = Field(ge=0, le=100000)
    knowledge: int = Field(ge=0, le=100)
    itn: int = Field(ge=0, le=100)
    myth: str
    test: str
    notes: str = Field(default="", max_length=5000)


class StatusUpdate(BaseModel):
    status: str


def serialize(r: Outreach):
    return {
        "id": str(r.id),
        "date": r.date.isoformat(),
        "type": r.type,
        "institution": r.institution,
        "male": r.male,
        "female": r.female,
        "total": r.total,
        "knowledge": r.knowledge,
        "itn": r.itn,
        "myth": r.myth,
        "test": r.test,
        "notes": r.notes or "",
        "priority": r.priority,
        "score": r.score,
        "reasons": [x for x in (r.reasons_text or "").split("|||") if x],
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@app.get("/")
def root():
    return {
        "service": "Rootslink Africa Malaria Outreach API",
        "status": "online",
        "purpose": "prototype"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/outreaches")
def list_outreaches(db: Session = Depends(get_db)):
    rows = db.query(Outreach).order_by(Outreach.id.asc()).all()
    return [serialize(r) for r in rows]


@app.post("/api/outreaches", status_code=201)
def create_outreach(payload: OutreachCreate, db: Session = Depends(get_db)):
    if payload.myth not in {"none", "some", "strong"}:
        raise HTTPException(status_code=422, detail="Invalid myth value.")
    if payload.test not in {"good", "mixed", "poor"}:
        raise HTTPException(status_code=422, detail="Invalid testing-practice value.")

    score, priority, reasons = priority_score(
        payload.knowledge, payload.itn, payload.myth, payload.test
    )

    row = Outreach(
        date=payload.date,
        type=payload.type.strip(),
        institution=payload.institution.strip(),
        male=payload.male,
        female=payload.female,
        total=payload.male + payload.female,
        knowledge=payload.knowledge,
        itn=payload.itn,
        myth=payload.myth,
        test=payload.test,
        notes=payload.notes.strip(),
        priority=priority,
        score=score,
        reasons_text="|||".join(reasons),
        status="Pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@app.patch("/api/outreaches/{outreach_id}/status")
def update_status(outreach_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    if payload.status not in {"Pending", "Scheduled", "Completed"}:
        raise HTTPException(status_code=422, detail="Status must be Pending, Scheduled, or Completed.")

    row = db.get(Outreach, outreach_id)
    if not row:
        raise HTTPException(status_code=404, detail="Outreach record not found.")

    row.status = payload.status
    db.commit()
    db.refresh(row)
    return serialize(row)


@app.delete("/api/outreaches/{outreach_id}")
def delete_outreach(outreach_id: int, db: Session = Depends(get_db)):
    row = db.get(Outreach, outreach_id)
    if not row:
        raise HTTPException(status_code=404, detail="Outreach record not found.")
    db.delete(row)
    db.commit()
    return {"deleted": True, "id": str(outreach_id)}


@app.delete("/api/outreaches")
def clear_outreaches(db: Session = Depends(get_db)):
    deleted = db.query(Outreach).delete()
    db.commit()
    return {"cleared": True, "deleted_records": deleted}


# Lightweight API versions of the two educational helpers.
# The frontend keeps its richer local display logic intact, but these endpoints
# make the backend architecture ready for future server-side use.

class FieldNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=10000)


@app.post("/api/malaguide/analyze")
def malaguide_analyze(payload: FieldNoteRequest):
    n = payload.note.lower()
    issues = []

    testing_phrases = [
        "without testing", "without a test", "without an rdt", "self-medication",
        "self medication", "every fever is malaria", "leftover malaria medicine",
        "stopping treatment early", "sharing malaria medicine",
        "did not complete the treatment", "treat themselves first",
        "medicine before visiting the clinic", "act from the pharmacy without"
    ]
    if any(p in n for p in testing_phrases):
        issues.append({
            "issue_category": "Medication taken without testing",
            "related_module": "Module 4: Test Before Treatment",
            "weight": 30,
            "priority_reason": "Treatment without diagnostic confirmation is a serious program concern.",
            "immediate_action": "Reinforce test-before-treatment education and appropriate care seeking.",
            "follow_up": "Revisit the group and check whether testing behavior improves.",
            "supervisor_review": True
        })

    pregnancy_phrases = ["pregnant", "missed anc", "missed antenatal", "missed iptp", "needs referral"]
    if ("pregnant" in n and any(p in n for p in pregnancy_phrases[1:])) or "needs referral" in n:
        issues.append({
            "issue_category": "Pregnancy malaria prevention / referral concern",
            "related_module": "Module 5: Protect Pregnant Women",
            "weight": 30,
            "priority_reason": "Pregnancy-related malaria prevention gaps need prompt follow-up.",
            "immediate_action": "Encourage prompt linkage to the appropriate ANC or health facility.",
            "follow_up": "Confirm linkage and reinforce ITN/IPTp education.",
            "supervisor_review": True
        })

    score = min(100, sum(i["weight"] for i in issues))
    priority = "High" if score >= 30 else "Medium" if score >= 15 else "Low"

    clarification = None
    if not issues and any(k in n for k in ["medicine", "drug", "act", "fever", "pharmacy", "rdt", "test"]):
        clarification = "I may have identified a test-before-treatment issue. Did participants report taking malaria medicine without first testing?"

    return {
        "priority": priority,
        "score": score,
        "issues": issues,
        "clarification": clarification
    }


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=3000)


@app.post("/api/malaria/ask")
def malaria_qa(payload: QuestionRequest):
    q = payload.question.lower()

    if any(k in q for k in ["cause", "causes", "get malaria", "mosquito"]):
        answer = "Malaria is transmitted to people through the bite of an infected female Anopheles mosquito."
        module = "Module 1: What Is Malaria?"
    elif any(k in q for k in ["prevent", "prevention", "net", "itn"]):
        answer = "Key prevention measures include sleeping under an insecticide-treated net every night and reducing mosquito breeding sites around homes."
        module = "Modules 3 and 6"
    elif any(k in q for k in ["test", "treatment", "medicine", "drug", "act"]):
        answer = "Not every fever is malaria. Suspected malaria should be assessed and tested by an appropriate health provider before antimalarial treatment."
        module = "Module 4: Test Before Treatment"
    elif any(k in q for k in ["pregnant", "pregnancy", "anc", "iptp"]):
        answer = "Pregnant women should attend antenatal care, use an insecticide-treated net, and receive malaria prevention services according to national guidance."
        module = "Module 5: Protect Pregnant Women"
    elif any(k in q for k in ["sign", "symptom", "fever", "headache"]):
        answer = "Possible malaria symptoms include fever, headache, chills, sweating, weakness, and body pains, but testing is important because fever can have different causes."
        module = "Module 2: Know the Signs"
    else:
        answer = "I can help with malaria causes, signs, prevention, mosquito nets, testing before treatment, pregnancy protection, and environmental prevention."
        module = "Education Center"

    return {
        "answer": answer,
        "related_module": module,
        "note": "Educational information only; this tool does not diagnose illness."
    }
