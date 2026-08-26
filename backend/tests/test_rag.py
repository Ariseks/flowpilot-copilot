from app.services.rag import LocalTfidfRetriever


def test_chinese_tokenization_and_chunk_overlap():
    retriever = LocalTfidfRetriever(chunk_size=20, overlap=4)
    terms = retriever.tokenize("企业版支持审计日志和 SAML SSO")
    assert "企业" in terms
    assert "审计" in terms
    assert "saml" in terms
    assert "sso" in terms

    chunks = retriever.split_text("第一句包含一些产品信息。第二句包含更多产品信息。第三句继续补充。")
    assert len(chunks) >= 2
    assert chunks[1].startswith(chunks[0][-4:])


def test_tfidf_retrieval_prefers_relevant_source():
    retriever = LocalTfidfRetriever()
    retriever.build(
        [
            {"id": "price", "source": "计费", "text": "专业版每月九十九元，支持两万次任务。"},
            {"id": "security", "source": "安全", "text": "企业版支持审计日志和单点登录。"},
        ]
    )
    result = retriever.search("企业版审计日志", top_k=1)
    assert result[0].source == "安全"
    assert result[0].score > 0
