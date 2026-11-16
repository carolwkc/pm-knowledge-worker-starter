import pytest

from pmknowledge.evaluation import EvaluationDataset, retrieval_metrics


def labelled_dataset(spans=None):
    return {
        "documents": [{"id": "a", "title": "Synthetic", "text": "🚀 First.\r\n\r\nSecond."}],
        "cases": [
            {
                "id": "q",
                "query": "first",
                "relevant_document_ids": ["a"],
                "evidence_spans": spans
                if spans is not None
                else [{"document_id": "a", "start_char": 2, "end_char": 8}],
            }
        ],
    }


@pytest.mark.parametrize(
    "spans",
    [
        [{"document_id": "a", "start_char": -1, "end_char": 8}],
        [{"document_id": "a", "start_char": 8, "end_char": 8}],
        [{"document_id": "a", "start_char": 2, "end_char": 200}],
        [{"document_id": "unknown", "start_char": 2, "end_char": 8}],
        [],
        [{"document_id": "a", "start_char": 2, "end_char": 8}] * 2,
    ],
)
def test_invalid_or_inconsistent_support_spans_are_rejected(spans):
    with pytest.raises(ValueError):
        EvaluationDataset.model_validate(labelled_dataset(spans))


def test_span_offsets_count_unicode_codepoints_and_preserve_crlf():
    dataset = EvaluationDataset.model_validate(labelled_dataset())
    span = dataset.cases[0].evidence_spans[0]
    assert dataset.documents[0].text[span.start_char : span.end_char] == "First."


def test_span_coverage_requires_containment_and_counts_each_gold_span_once():
    from uuid import uuid4

    from pmknowledge.evaluation import EvaluationSpan, span_coverage
    from pmknowledge.schemas import Citation

    document = uuid4()

    def citation(start, end):
        return Citation(
            source_document_id=document,
            document_version_id=uuid4(),
            chunk_id=uuid4(),
            title="Synthetic",
            external_uri=None,
            ordinal=0,
            excerpt="x" * (end - start),
            start_char=start,
            end_char=end,
            citation="1",
        )

    spans = [
        EvaluationSpan(document_id="a", start_char=2, end_char=8),
        EvaluationSpan(document_id="a", start_char=12, end_char=19),
    ]
    assert span_coverage(
        spans, [citation(0, 10), citation(0, 10), citation(13, 20)], {str(document): "a"}
    ) == (2, 1)


def test_evidence_metrics_include_false_positive_negatives_and_positive_abstention():
    from pmknowledge.evaluation import answer_metrics

    metrics = answer_metrics(
        [
            {"emitted": 2, "valid": 2, "relevant": 1, "covered": 2, "expected": 2},
            {"emitted": 0, "valid": 0, "relevant": 0, "covered": 0, "expected": 1},
            {"emitted": 1, "valid": 1, "relevant": 0, "covered": 0, "expected": 0},
        ]
    )
    assert metrics["evidence_precision"] == {"value": 1 / 3, "numerator": 1, "denominator": 3}
    assert metrics["evidence_recall"] == {"value": 0.5, "numerator": 1.0, "denominator": 2}
    assert metrics["citation_integrity"]["value"] == 1
    assert metrics["negative_abstention"] == {"value": 0, "numerator": 0, "denominator": 1}
    assert metrics["positive_abstention"] == {"value": 0.5, "numerator": 1, "denominator": 2}


def test_empty_denominators_and_legacy_support_labels_are_null():
    from pmknowledge.evaluation import answer_metrics

    assert answer_metrics([])["citation_integrity"]["value"] is None
    metrics = answer_metrics(
        [{"emitted": 1, "valid": 1, "relevant": None, "covered": None, "expected": None}]
    )
    assert metrics["evidence_precision"]["value"] is None
    assert metrics["evidence_recall"]["value"] is None
    assert metrics["negative_abstention"]["value"] is None
    assert metrics["positive_abstention"]["value"] is None


def test_pilot_corpus_has_authored_spans_and_balanced_cohorts():
    from collections import Counter
    from pathlib import Path

    dataset = EvaluationDataset.model_validate_json(
        Path("apps/api/evaluation/pilot-cases.json").read_bytes()
    )
    assert len(dataset.documents) == 20
    assert Counter(case.category for case in dataset.cases) == {
        "lexical": 10,
        "paraphrase": 10,
        "multi_source": 10,
        "missing_evidence": 10,
    }
    for case in dataset.cases:
        assert len(case.relevant_document_ids) == (
            2
            if case.category == "multi_source"
            else 0
            if case.category == "missing_evidence"
            else 1
        )
    assert any("\r\n" in document.text for document in dataset.documents)
    assert any("🚀" in document.text for document in dataset.documents)


def test_partial_support_annotation_cannot_silently_exclude_cases_from_metrics():
    raw = labelled_dataset()
    raw["cases"].append({"id": "unlabelled", "query": "second", "relevant_document_ids": ["a"]})
    with pytest.raises(ValueError, match="every case"):
        EvaluationDataset.model_validate(raw)


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
