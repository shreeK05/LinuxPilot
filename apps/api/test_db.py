from app.db.session import SessionLocal
from app.agent.models import VerificationResult
from app.repositories.agent_repo import log_audit_event
import uuid
import traceback

db = SessionLocal()
try:
    res = VerificationResult(
        success=False,
        expected_state="Some state",
        actual_state="Error executing semantic verification",
        error="Mock error with 'quotes' and \n newlines",
        verification_method="semantic",
        retry_suggested=False,
        diff={"error": "Failed to generate structured response"}
    )
    
    from app.models.domain import Task
    task = db.query(Task).first()
    if task:
        log_audit_event(db, task.id, "TEST_EVENT", "FAILED", res.model_dump())
        print("SUCCESSFULLY LOGGED AUDIT EVENT")
    else:
        print("No task found to test against")
except Exception as e:
    print(f"FAILED TO LOG: {e}")
    traceback.print_exc()
finally:
    db.close()
