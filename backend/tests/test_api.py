from io import BytesIO

from docx import Document


def test_health_and_dashboard_are_ready_in_demo_mode(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["mode"] == "demo"
    assert health.json()["documents"] >= 7
    assert health.json()["chunks"] >= 7

    assert client.get("/api/health/live").json() == {"status": "ok", "check": "liveness"}
    readiness = client.get("/api/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["check"] == "readiness"
    assert readiness.json()["documents"] >= 7

    metrics = client.get("/api/dashboard/metrics").json()
    assert metrics["feedback_count"] >= 3
    assert metrics["average_rating"] > 0
    assert metrics["document_categories"]["FAQ"] == 2


def test_runtime_metrics_include_request_counts_and_latency(client):
    assert client.get("/api/health/live").status_code == 200
    response = client.get("/api/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["requests_total"] >= 2
    assert body["responses_total"] >= 1
    assert body["by_path"]["/api/health/live"] >= 1
    assert body["latency_ms"]["count"] >= 1


def test_lightweight_rate_limit_returns_retry_hint(rate_limited_client):
    assert rate_limited_client.get("/api/health/live").status_code == 200
    limited = rate_limited_client.get("/api/health/live")
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
    assert "频繁" in limited.json()["detail"]


def test_documents_list_import_and_upload(client):
    before = client.get("/api/documents").json()
    imported = client.post(
        "/api/documents/import",
        json={
            "title": "退款规则补充",
            "text": "FlowPilot 退款申请需要在购买后七天内提交。",
            "category": "FAQ",
        },
    )
    assert imported.status_code == 201
    assert imported.json()["chunk_count"] == 1

    uploaded = client.post(
        "/api/documents/upload",
        files={"file": ("guide.txt", "批量操作功能支持一次移动多个流程。", "text/plain")},
    )
    assert uploaded.status_code == 201
    assert len(client.get("/api/documents").json()) == len(before) + 2


def test_docx_upload_extracts_text(client):
    document = Document()
    document.add_paragraph("DOCX 文件支持导入并建立检索索引。")
    buffer = BytesIO()
    document.save(buffer)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("guide.docx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 201
    assert response.json()["title"] == "guide"


def test_chat_returns_ranked_citations_and_is_deterministic(client):
    payload = {"message": "专业版每月多少钱，有多少任务额度？", "top_k": 3}
    first = client.post("/api/chat", json=payload)
    second = client.post("/api/chat", json=payload)
    assert first.status_code == 200
    assert first.json()["mode"] == "demo"
    assert first.json()["answer"] == second.json()["answer"]
    citations = first.json()["citations"]
    assert citations
    assert {"source", "chunk", "score", "chunk_id"} <= citations[0].keys()
    assert "99" in first.json()["answer"]
    assert all(citations[i]["score"] >= citations[i + 1]["score"] for i in range(len(citations) - 1))


def test_agent_routes_returns_trace_and_supports_replay(client):
    response = client.post(
        "/api/agent/tasks",
        json={"input": "请分析近期客户反馈痛点和满意度", "intent": "auto"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["intent"] == "feedback_analysis"
    assert body["status"] == "completed"
    assert len(body["steps"]) == 3
    assert body["artifacts"]["type"] == "feedback_report"
    assert body["artifacts"]["recommendations"]
    assert body["trace"]["retrieval"]["citation_count"] >= 1
    assert body["trace"]["generation"]["fallback_used"] is True
    replay = client.get(f"/api/agent/tasks/{body['id']}")
    assert replay.status_code == 200
    assert replay.json()["id"] == body["id"]


def test_explicit_agent_intents_are_supported(client):
    cases = {
        "knowledge_qa": "knowledge_answer",
        "customer_reply": "customer_reply",
        "campaign_plan": "campaign_plan",
    }
    for intent, artifact_type in cases.items():
        response = client.post(
            "/api/agent/tasks", json={"input": "介绍 FlowPilot", "intent": intent}
        )
        assert response.status_code == 201
        assert response.json()["artifacts"]["type"] == artifact_type


def test_demo_customer_reply_is_concise_and_does_not_dump_sources(client):
    response = client.post(
        "/api/agent/tasks",
        json={
            "input": "升级专业版后仍显示500次额度，请生成客服回复",
            "intent": "customer_reply",
            "top_k": 4,
        },
    )
    assert response.status_code == 201
    body = response.json()
    reply = body["artifacts"]["reply"]
    assert body["mode"] == "demo"
    assert "来源：" not in reply
    assert "片段：" not in reply
    assert "根据 FlowPilot 知识库" not in reply
    assert len(reply) < 500


def test_feedback_is_linked_to_task_and_generates_real_insights(client):
    task = client.post(
        "/api/agent/tasks",
        json={"input": "流程失败参数错误怎么办？", "intent": "knowledge_qa"},
    ).json()
    feedback = client.post(
        "/api/feedback",
        json={
            "task_id": task["id"],
            "message": task["input"],
            "rating": 2,
            "category": "copilot_answer",
        },
    )
    assert feedback.status_code == 201
    assert feedback.json()["task_id"] == task["id"]
    insights = client.get("/api/insights")
    assert insights.status_code == 200
    assert insights.json()["low_scores"][0]["task_id"] == task["id"]
    assert insights.json()["gaps"]


def test_feedback_and_versioned_evaluation(client, persisted_state):
    feedback = client.post(
        "/api/feedback",
        json={"message": "希望增加更多模板", "rating": 4, "category": "模板"},
    )
    assert feedback.status_code == 201
    assert feedback.json()["id"].startswith("fb-")
    assert len(client.get("/api/feedback").json()) >= 4
    assert any(item["message"] == "测试持久化" for item in persisted_state["feedback"])

    evaluation = client.post("/api/evaluation", json={})
    assert evaluation.status_code == 200
    body = evaluation.json()
    assert body["total"] == 20
    assert body["dataset_version"] == "v1.0"
    assert body["retrieval_hit_rate"] > 0
    assert body["source_recall_at_k"] is not None
    assert body["refusal_accuracy"] is not None
    assert body["baseline"]["strategy"] == "tfidf"
    assert body["hybrid"]["strategy"] == "rrf"
    assert body["citation_correctness"] is not None
    assert body["faithfulness"] is not None
    assert body["cases"][0]["unsupported_claims"] == [] or isinstance(body["cases"][0]["unsupported_claims"], list)


def test_task_history_supports_filters_pagination_and_trace_strategy(client):
    created = client.post(
        "/api/agent/tasks",
        json={"input": "专业版每月多少钱？", "intent": "knowledge_qa"},
    )
    assert created.status_code == 201
    assert created.json()["trace"]["retrieval"]["strategy"] == "rrf"

    history = client.get("/api/agent/tasks?limit=1&intent=knowledge_qa")
    assert history.status_code == 200
    payload = history.json()
    assert payload["total"] >= 1
    assert len(payload["items"]) == 1
    assert {"items", "total", "next_cursor"} <= payload.keys()


def test_hybrid_retrieval_is_ranked_and_keeps_source_metadata(client):
    response = client.post(
        "/api/chat", json={"message": "任务运行次数如何计算？", "top_k": 4}
    )
    assert response.status_code == 200
    citations = response.json()["citations"]
    assert citations
    assert all({"source", "chunk", "score", "chunk_id"} <= item.keys() for item in citations)
    assert all(citations[index]["score"] >= citations[index + 1]["score"] for index in range(len(citations) - 1))
