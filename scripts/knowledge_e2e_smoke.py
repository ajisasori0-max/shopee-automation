"""End-to-end smoke test for the knowledge layer."""

import os
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.knowledge.index import KnowledgeIndex
from commerceos.knowledge.models import KnowledgeNote
from commerceos.knowledge.organizational_memory import OrganizationalMemory
from commerceos.knowledge.retrieval_engine import MemoryRetrievalEngine
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork, sqlalchemy_knowledge_uow
from commerceos.knowledge.vault import ObsidianVault
from commerceos.knowledge.writer import ObsidianWriter
from commerceos.platform.database.connection import create_all, get_session, reset_engine


def main():
    db_path = "test_knowledge_e2e.db"
    reset_engine()
    if os.path.exists(db_path):
        os.remove(db_path)

    db_url = f"sqlite:///{db_path}"
    create_all(db_url)
    session = get_session(db_url)

    vault_dir = Path("test_knowledge_vault").resolve()
    if vault_dir.exists():
        import shutil

        shutil.rmtree(vault_dir)
    vault_dir.mkdir()

    try:
        uow = SQLAlchemyKnowledgeUnitOfWork(session)
        vault = ObsidianVault(vault_dir)
        vault.ensure_structure()
        writer = ObsidianWriter(vault_dir)

        # 1. Write a daily note.
        path = writer.write(
            note_type="daily",
            note_id="kn-2026-07-29",
            title="Daily COO Brief — 2026-07-29",
            body="## Business State\n\nRevenue healthy.\n",
            note_date=date(2026, 7, 29),
            tags=["daily", "business", "revenue"],
            links=["decision:d1"],
        )
        print(f"1. Daily note written: {path}")

        # 2. Persist metadata.
        with sqlalchemy_knowledge_uow(session) as uow_ctx:
            note = KnowledgeNote(
                note_id="kn-2026-07-29",
                note_type="daily",
                note_date=date(2026, 7, 29),
                title="Daily COO Brief — 2026-07-29",
                path=str(path.relative_to(vault_dir)),
                tags=["daily", "business", "revenue"],
                links=["decision:d1"],
                source_domains=["intelligence"],
            )
            uow_ctx.notes().save(note)

        # 3. Generate index.
        index = KnowledgeIndex(vault_dir, repository=uow.notes())
        index_path = index.generate()
        print(f"2. Index written: {index_path}")

        # 4. Organizational memory: create lesson and experiment.
        org = OrganizationalMemory(uow.notes(), vault_dir=vault_dir)
        lesson = org.create_lesson("Test lesson", "Always verify revenue before decisions.", related_note_ids=["kn-2026-07-29"])
        experiment = org.create_experiment("Test experiment", "Discounts improve orders", "Orders increase 10%")
        sop = org.create_sop("Test SOP", ["Check data freshness", "Generate daily brief", "Review decisions"])
        project = org.create_project_note("CommerceOS", "Active", ["WP3.1 closed", "WP3.2 in progress"])
        print(f"3. Lesson: {lesson['note_id']}")
        print(f"4. Experiment: {experiment['note_id']}")
        print(f"5. SOP: {sop['note_id']}")
        print(f"6. Project: {project['note_id']}")

        # 5. Retrieval engine queries.
        from commerceos.knowledge.dashboard import KnowledgeDashboard

        dash = KnowledgeDashboard(uow.notes(), vault_dir=vault_dir)
        engine = MemoryRetrievalEngine(dash)
        history = engine.project_history("CommerceOS", days=30)
        print(f"7. Project history notes: {history['note_count']}")

        timeline = engine.timeline_around_metric("revenue", days=30)
        print(f"8. Revenue metric notes: {timeline['note_count']}")

        print("✅ E2E knowledge smoke test passed.")
    finally:
        session.close()
        reset_engine()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()
