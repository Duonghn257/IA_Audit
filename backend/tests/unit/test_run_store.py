from app.infrastructure.run_store import InMemoryRunStore


def test_run_store_tracks_progress_and_completion() -> None:
    store = InMemoryRunStore()
    run = store.create("/data/project", "/backend/issues.json")

    store.mark_running(run.run_id)
    event = store.append_progress(
        run.run_id,
        stage="PARSING",
        message="Parsing AWP...",
        completed_steps=1,
        total_steps=8,
        warning=False,
    )
    store.mark_completed(
        run.run_id,
        output_path="/data/project/Output/v0.1/report.docx",
        version="v0.1",
        issue_count=2,
    )

    saved = store.get(run.run_id)
    assert saved.status == "COMPLETED"
    assert saved.output_path.endswith("report.docx")
    assert saved.events == [event]
    assert store.list_events(run.run_id, after_event_id=event.event_id) == []

