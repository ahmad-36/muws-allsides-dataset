"""Semantic chunking utilities shared by encoder and NLI runners."""

import re
import numpy as np


def split_sentences(text):
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z“”"‘’\'])', text)
    return [s.strip() for s in parts if s.strip()]


def semantic_chunk(text, tokenizer, max_chunk_tokens=510):
    """Split text into chunks of complete sentences, each <= max_chunk_tokens."""
    full_tokens = tokenizer(text, add_special_tokens=False)["input_ids"]
    if len(full_tokens) <= max_chunk_tokens:
        return [text]

    sentences = split_sentences(text)
    if not sentences:
        return [text]

    sent_token_lens = []
    for s in sentences:
        toks = tokenizer(s, add_special_tokens=False)["input_ids"]
        sent_token_lens.append(len(toks))

    chunks = []
    current_sents = []
    current_len = 0

    for sent, tok_len in zip(sentences, sent_token_lens):
        if tok_len > max_chunk_tokens:
            if current_sents:
                chunks.append(" ".join(current_sents))
                current_sents, current_len = [], 0
            chunks.append(sent)
            continue

        if current_len + tok_len > max_chunk_tokens and current_sents:
            chunks.append(" ".join(current_sents))
            current_sents, current_len = [], 0

        current_sents.append(sent)
        current_len += tok_len

    if current_sents:
        chunks.append(" ".join(current_sents))

    return chunks


def aggregate_logits(all_logits):
    """Mean-pool logits across chunks, return predicted class index and mean logits."""
    mean_logits = np.mean(all_logits, axis=0)
    return int(np.argmax(mean_logits)), mean_logits.tolist()
