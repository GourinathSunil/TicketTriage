"""
Feature engineering and text vectorization for support ticket triage.
Combines TF-IDF word n-grams and character n-grams over ticket subject and body.
"""
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import MultiLabelBinarizer


def build_text_corpus(df: pd.DataFrame) -> List[str]:
    """
    Combines subject and body.
    Weights subject by repeating it to emphasize salient keywords.
    """
    subjects = df["subject"].fillna("").astype(str).tolist()
    bodies = df["body"].fillna("").astype(str).tolist()
    # Emphasize subject 2x
    return [f"{s} {s} {b}".strip() for s, b in zip(subjects, bodies)]


def create_feature_pipeline(max_features: int = 15000) -> FeatureUnion:
    """
    Creates a FeatureUnion of:
    1. Word n-grams (1-2) with sublinear term frequency
    2. Character n-grams (3-5) with word boundaries to capture typos, error codes, and technical jargon
    """
    word_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=int(max_features * 0.65),
        sublinear_tf=True,
        min_df=2,
        stop_words="english",
    )
    char_vectorizer = TfidfVectorizer(
        ngram_range=(3, 5),
        analyzer="char_wb",
        max_features=int(max_features * 0.35),
        sublinear_tf=True,
        min_df=3,
    )

    union = FeatureUnion([
        ("word_tfidf", word_vectorizer),
        ("char_tfidf", char_vectorizer),
    ])
    return union


class TicketFeatureExtractor:
    """Wrapper managing vectorizer and MultiLabelBinarizer."""

    def __init__(self, domain_label_ids: List[str], max_features: int = 15000):
        self.domain_label_ids = list(domain_label_ids)
        self.vectorizer = create_feature_pipeline(max_features=max_features)
        self.mlb = MultiLabelBinarizer(classes=self.domain_label_ids)

    def fit(self, df: pd.DataFrame) -> "TicketFeatureExtractor":
        corpus = build_text_corpus(df)
        self.vectorizer.fit(corpus)
        self.mlb.fit(df["labels_list"])
        return self

    def transform_x(self, df: pd.DataFrame):
        corpus = build_text_corpus(df)
        return self.vectorizer.transform(corpus)

    def transform_y(self, df: pd.DataFrame) -> np.ndarray:
        return self.mlb.transform(df["labels_list"])

    def transform_single(self, subject: str, body: str):
        combined = f"{subject} {subject} {body}".strip()
        return self.vectorizer.transform([combined])
