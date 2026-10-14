"""Tests for real-time SSE event streaming and Workflow execution events."""

import asyncio
import json
import time
from fastapi.testclient import TestClient
import httpx
import pytest
from app.api.main import app
from app.models.research import ResearchRun, RunStatus
from app.services.event_stream import EventBroadcaster, RunEvent, event_broadcaster
from app.services.workflow_manager import workflow_manager


def test_event_broadcaster_pub_sub() -> None:
    broadcaster = EventBroadcaster()
    run_id = "RUN_TEST_BROADCAST_001"

    broadcaster.publish(run_id, "TEST_INIT", "Testing init event", {"round": 1})
    broadcaster.publish(run_id, "RUN_COMPLETED", "Done", {"status": "SUCCESS"})

    events_received: list[dict] = []
    for sse_chunk in broadcaster.subscribe(run_id):
        if sse_chunk.startswith("data: "):
            payload = json.loads(sse_chunk[6:].strip())
            events_received.append(payload)

    assert len(events_received) == 2
    assert events_received[0]["event_type"] == "TEST_INIT"
    assert events_received[0]["data"]["round"] == 1
    assert events_received[1]["event_type"] == "RUN_COMPLETED"


def test_event_broadcaster_history_replay() -> None:
    broadcaster = EventBroadcaster()
    run_id = "RUN_TEST_HIST_002"

    broadcaster.publish(run_id, "EVENT_1", "Message 1")
    broadcaster.publish(run_id, "EVENT_2", "Message 2")
    broadcaster.publish(run_id, "RUN_COMPLETED", "Finished")

    collected = []
    for chunk in broadcaster.subscribe(run_id):
        if chunk.startswith("data: "):
            collected.append(json.loads(chunk[6:].strip()))

    assert len(collected) == 3
    assert collected[0]["event_type"] == "EVENT_1"
    assert collected[1]["event_type"] == "EVENT_2"
    assert collected[2]["event_type"] == "RUN_COMPLETED"


def test_sse_endpoint_validation() -> None:
    client = TestClient(app)
    # Unknown run returns 404
    res = client.get("/api/runs/NON_EXISTENT_RUN/events")
    assert res.status_code == 404


def test_workflow_async_execution_with_streaming() -> None:
    client = TestClient(app)

    res = client.post("/api/runs", json={
        "ticker_or_name": "MSFT",
        "objective": "Async workflow streaming acceptance test",
    })
    assert res.status_code == 200
    run_id = res.json()["run"]["run_id"]

    # Approve with async_execution = True
    approve_res = client.post(f"/api/runs/{run_id}/approvals", json={
        "decision": "APPROVED",
        "async_execution": True,
    })
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "RESEARCHING"

    # Listen to SSE until completion
    completed = False
    start_time = time.time()
    for sse_chunk in event_broadcaster.subscribe(run_id):
        if sse_chunk.startswith("data: "):
            payload = json.loads(sse_chunk[6:].strip())
            if payload["event_type"] == "RUN_COMPLETED":
                completed = True
                break
            if payload["event_type"] == "RUN_FAILED":
                break
        if time.time() - start_time > 20:
            break

    assert completed is True

    # Check that final report and PDF are persisted
    run_final = client.get(f"/api/runs/{run_id}").json()
    assert run_final["status"] in ["COMPLETE", "REQUIRES_REVIEW"]

    report_res = client.get(f"/api/runs/{run_id}/report")
    assert report_res.status_code == 200

    pdf_res = client.get(f"/api/runs/{run_id}/report/pdf")
    assert pdf_res.status_code == 200
