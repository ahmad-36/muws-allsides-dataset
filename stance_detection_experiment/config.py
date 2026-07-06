import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CONDITIONED_DIR = DATA_DIR / "conditioned"
RESULTS_DIR = BASE_DIR / "results"
ANALYSIS_DIR = BASE_DIR / "analysis"

for d in [DATA_DIR, CONDITIONED_DIR, RESULTS_DIR, ANALYSIS_DIR,
          ANALYSIS_DIR / "confusion_matrices", ANALYSIS_DIR / "figures"]:
    d.mkdir(parents=True, exist_ok=True)

MULTI_SOURCE_DIR = Path("/nfs/home/abdullaha/qbias/Qbias/multi_source_scrape/output/per_domain_clean")
ALLSIDES_CSV = Path("/nfs/home/abdullaha/qbias/Qbias/archive/allsides_balanced_news_headlines-texts.csv")

MODEL_ENCODER = "premsa/political-bias-prediction-allsides-DeBERTa"
MODEL_NLI = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
MODEL_LLM = "Qwen/Qwen2.5-14B-Instruct"

LABEL_3CLASS = ["left", "center", "right"]
LABEL_5CLASS = ["left", "lean_left", "center", "lean_right", "right"]

FIVE_TO_THREE = {
    "left": "left",
    "lean left": "left",
    "lean_left": "left",
    "center": "center",
    "lean right": "right",
    "lean_right": "right",
    "right": "right",
}

NLI_HYPOTHESES_3CLASS = {
    "left": "This article has a left-wing political perspective.",
    "center": "This article has a centrist political perspective.",
    "right": "This article has a right-wing political perspective.",
}

NLI_HYPOTHESES_5CLASS = {
    "left": "This article has a left-wing political perspective.",
    "lean_left": "This article has a moderately left-leaning political perspective.",
    "center": "This article has a centrist political perspective.",
    "lean_right": "This article has a moderately right-leaning political perspective.",
    "right": "This article has a right-wing political perspective.",
}

LLM_SYSTEM_PROMPT = (
    "You are a political media analyst. Classify the political stance of news "
    "articles based solely on content, framing, word choice, and editorial "
    "perspective. Do not consider the publication source."
)

LLM_USER_PROMPT_3CLASS = (
    "Classify this article's political stance.\n"
    "Respond with exactly one label: left, center, or right.\n\n"
    "Article:\n{article_text}\n\nStance:"
)

LLM_USER_PROMPT_5CLASS = (
    "Classify this article's political stance.\n"
    "Respond with exactly one label: left, lean_left, center, lean_right, or right.\n\n"
    "Article:\n{article_text}\n\nStance:"
)

PUBLISHER_REGISTRY = {
    "cnn.com": {
        "display_name": "CNN",
        "names": ["CNN", "Cable News Network", "cnn.com", "CNN's"],
        "rating_5class": "lean left",
        "rating_3class": "left",
        "cross_swap": "foxnews.com",
        "same_swap": "nbcnews.com",
    },
    "foxnews.com": {
        "display_name": "Fox News",
        "names": ["Fox News", "Fox News Digital", "foxnews.com", "Fox News'"],
        "rating_5class": "right",
        "rating_3class": "right",
        "cross_swap": "cnn.com",
        "same_swap": "nypost.com",
    },
    "nytimes.com": {
        "display_name": "The New York Times",
        "names": ["New York Times", "The New York Times", "NYT", "nytimes.com", "The Times"],
        "rating_5class": "lean left",
        "rating_3class": "left",
        "cross_swap": "nypost.com",
        "same_swap": "washingtonpost.com",
    },
    "nypost.com": {
        "display_name": "New York Post",
        "names": ["New York Post", "NY Post", "nypost.com"],
        "rating_5class": "lean right",
        "rating_3class": "right",
        "cross_swap": "nytimes.com",
        "same_swap": "washingtonexaminer.com",
    },
    "washingtonpost.com": {
        "display_name": "The Washington Post",
        "names": ["Washington Post", "The Washington Post", "WaPo", "washingtonpost.com"],
        "rating_5class": "lean left",
        "rating_3class": "left",
        "cross_swap": "washingtonexaminer.com",
        "same_swap": "nytimes.com",
    },
    "washingtonexaminer.com": {
        "display_name": "Washington Examiner",
        "names": ["Washington Examiner", "washingtonexaminer.com"],
        "rating_5class": "lean right",
        "rating_3class": "right",
        "cross_swap": "washingtonpost.com",
        "same_swap": "nypost.com",
    },
    "apnews.com": {
        "display_name": "Associated Press",
        "names": ["Associated Press", "AP News", "AP", "apnews.com"],
        "rating_5class": "left",
        "rating_3class": "left",
        "cross_swap": "foxnews.com",
        "same_swap": "theguardian.com",
    },
    "theguardian.com": {
        "display_name": "The Guardian",
        "names": ["The Guardian", "Guardian", "theguardian.com"],
        "rating_5class": "left",
        "rating_3class": "left",
        "cross_swap": "foxnews.com",
        "same_swap": "apnews.com",
    },
    "nbcnews.com": {
        "display_name": "NBC News",
        "names": ["NBC News", "NBC", "nbcnews.com"],
        "rating_5class": "lean left",
        "rating_3class": "left",
        "cross_swap": "foxbusiness.com",
        "same_swap": "cnn.com",
    },
    "politico.com": {
        "display_name": "Politico",
        "names": ["Politico", "POLITICO", "politico.com"],
        "rating_5class": "lean left",
        "rating_3class": "left",
        "cross_swap": "washingtonexaminer.com",
        "same_swap": "nbcnews.com",
    },
    "reuters.com": {
        "display_name": "Reuters",
        "names": ["Reuters", "reuters.com"],
        "rating_5class": "center",
        "rating_3class": "center",
        "cross_swap": "reuters.com",
        "same_swap": "bbc.com",
    },
    "bbc.com": {
        "display_name": "BBC",
        "names": ["BBC", "BBC News", "bbc.com"],
        "rating_5class": "center",
        "rating_3class": "center",
        "cross_swap": "bbc.com",
        "same_swap": "reuters.com",
    },
    "thehill.com": {
        "display_name": "The Hill",
        "names": ["The Hill", "thehill.com"],
        "rating_5class": "center",
        "rating_3class": "center",
        "cross_swap": "thehill.com",
        "same_swap": "newsweek.com",
    },
    "newsweek.com": {
        "display_name": "Newsweek",
        "names": ["Newsweek", "newsweek.com"],
        "rating_5class": "center",
        "rating_3class": "center",
        "cross_swap": "newsweek.com",
        "same_swap": "thehill.com",
    },
    "foxbusiness.com": {
        "display_name": "Fox Business",
        "names": ["Fox Business", "Fox Business Network", "foxbusiness.com"],
        "rating_5class": "lean right",
        "rating_3class": "right",
        "cross_swap": "nbcnews.com",
        "same_swap": "washingtonexaminer.com",
    },
}


def build_strip_pattern(domain):
    names = PUBLISHER_REGISTRY[domain]["names"]
    escaped = [re.escape(n) for n in sorted(names, key=len, reverse=True)]
    return re.compile(r'\b(' + '|'.join(escaped) + r')\b', re.IGNORECASE)


def strip_publisher(text, domain):
    pattern = build_strip_pattern(domain)
    return pattern.sub("the news outlet", text)


def swap_publisher(text, source_domain, target_domain):
    source_info = PUBLISHER_REGISTRY[source_domain]
    target_info = PUBLISHER_REGISTRY[target_domain]
    result = text
    for name in sorted(source_info["names"], key=len, reverse=True):
        result = re.sub(
            r'\b' + re.escape(name) + r'\b',
            target_info["display_name"],
            result,
            flags=re.IGNORECASE,
        )
    return result
