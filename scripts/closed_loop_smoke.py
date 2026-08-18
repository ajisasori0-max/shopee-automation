"""End-to-end smoke test for closed-loop outcome tracking."""

import os
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.closed_loop.service import OutcomeTracker
from commerceos.config.settings import get_settings
from commerceos.decision.constants import DecisionStatus
from commerceos.decision.models import Decision
from commerceos.execution.models import ExecutionPlan
from commerceos.platform.database.connection import create_all, get_session, reset_engine


def main():
    db_path = "test_closed_loop.db"
    reset_engine()
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists("test_closed_loop_vault"):
        import shutil
        shutil.rmtree("test_closed_loop_vault")

    db_url = f"sqlite:///{db_path}"
    create_all(db_url)
    session = get_session(db_url)

    try:
        # Seed a decision and execution plan.
        decision = Decision(
            category="revenue",
            severity="high",
            title="Test budget increase",
            description="Increase campaign budget by 20%.",
            rationale="ROAS is above target.",
            recommended_action="Increase budget.",
            expected_impact={"roas": 2.0, "revenue": 1.2},
            status=DecisionStatus.APPROVED.value,
        )
        session.add(decision)
        session.flush()

        plan = ExecutionPlan(
            decision_id=decision.id,
            action_type="ads_budget",
            status="succeeded",
            payload={"budget_delta": 0.2},
        )
        session.add(plan)
        session.flush()

        settings = get_settings()
        vault_dir = Path("test_closed_loop_vault").resolve()
        vault_dir.mkdir(exist_ok=True)

        tracker = OutcomeTracker(session=session, vault_dir=vault_dir)

        # 1. Capture execution feedback.
        outcome = tracker.capture_execution_feedback(
            execution_plan_id=plan.id,
            success=True,
            impact={"roas": 2.18, "revenue": 1.15},
        )
        print(f"1. Outcome recorded: {outcome.id}, success={outcome.success}")

        # 2. Update lessons.
        tracker.update_lessons(outcome.id, ["Budget scaling worked when ROAS was above 2.0x."])
        print("2. Lessons updated.")

        # 3. Promote to memory.
        memory = tracker.promote_to_memory(outcome.id)
        print(f"3. Memory note created: {memory['note_id']}")

        session.commit()
        print("✅ Closed-loop smoke test passed.")
    finally:
        session.close()
        reset_engine()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()
