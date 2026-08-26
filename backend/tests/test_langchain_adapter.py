def test_langchain_rag_returns_documents_and_citations(client):
    response = client.post(
        "/api/langchain/chat",
        json={"message": "专业版每月多少钱？", "top_k": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["framework"] == "langchain-core"
    assert payload["mode"] == "demo"
    assert len(payload["documents"]) == 3
    assert payload["documents"][0]["metadata"]["source"]
    assert payload["citations"][0]["chunk_id"]
    assert "99" in payload["answer"]
