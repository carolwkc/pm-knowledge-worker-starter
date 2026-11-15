import pytest

from pmknowledge.evaluation import EvaluationDataset, retrieval_metrics


def test_recall_and_reciprocal_rank_use_expected_documents_and_cutoff():
    metrics = retrieval_metrics(
        rankings=[["b", "a", "c"], ["b"], []],
        relevant=[{"a", "c"}, {"b"}, {"x"}],
        k=2,
    )
    assert metrics["recall_at_k"] == pytest.approx(0.5)
    assert metrics["mrr_at_k"] == pytest.approx(0.5)


def test_negative_cases_measure_abstention_separately_from_recall():
    metrics = retrieval_metrics(
        rankings=[[], ["unrelated"], ["a"]], relevant=[set(), set(), {"a"}], k=3
    )
    assert metrics["recall_at_k"] == 1.0
    assert metrics["mrr_at_k"] == 1.0
    assert metrics["no_evidence_accuracy"] == 0.5


def test_metrics_do_not_count_duplicate_documents_as_extra_recall():
    metrics = retrieval_metrics(rankings=[["a", "a"]], relevant=[{"a", "b"}], k=2)
    assert metrics["recall_at_k"] == 0.5


def test_unknown_gold_document_ids_cannot_produce_misleading_metrics():
    with pytest.raises(ValueError, match="known evaluation document IDs"):
        EvaluationDataset.model_validate(
            {
                "documents": [{"id": "known", "title": "Synthetic", "text": "Synthetic evidence."}],
                "cases": [{"id": "q", "query": "question", "relevant_document_ids": ["unknown"]}],
            }
        )


def test_duplicate_fixture_ids_are_rejected():
    document = {"id": "duplicate", "title": "Synthetic", "text": "Synthetic evidence."}
    with pytest.raises(ValueError, match="IDs must be unique"):
        EvaluationDataset.model_validate(
            {
                "documents": [document, document],
                "cases": [{"id": "q", "query": "question", "relevant_document_ids": ["duplicate"]}],
            }
        )
