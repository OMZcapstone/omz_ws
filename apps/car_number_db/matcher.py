# matcher.py
from rapidfuzz.distance import Levenshtein

# OCR에서 자주 헷갈리는 문자쌍(필요하면 계속 추가)
CONFUSION = {
    "0": ["0", "O"],
    "O": ["O", "0"],
    "1": ["1", "I"],
    "I": ["I", "1"],
    "5": ["5", "S"],
    "S": ["S", "5"],
    "8": ["8", "B"],
    "B": ["B", "8"],
}

def normalize(text: str) -> str:
    """공백/하이픈 제거, 대문자화 등 기본 정규화"""
    return (
        text.replace(" ", "")
            .replace("-", "")
            .upper()
            .strip()
    )

def generate_variants(ocr_text: str, max_edits: int = 2) -> set[str]:
    """
    OCR 결과에서 혼동 문자 교체로 후보 생성
    - max_edits: 최대 몇 글자까지 교체할지
    """
    s = normalize(ocr_text)
    variants = {s}

    # 1글자 교체 후보
    for i, ch in enumerate(s):
        if ch in CONFUSION:
            for rep in CONFUSION[ch]:
                if rep != ch:
                    variants.add(s[:i] + rep + s[i+1:])

    if max_edits <= 1:
        return variants

    # 2글자 교체 후보(간단하게 1글자 후보를 다시 확장)
    expanded = set(variants)
    for v in list(variants):
        for i, ch in enumerate(v):
            if ch in CONFUSION:
                for rep in CONFUSION[ch]:
                    if rep != ch:
                        expanded.add(v[:i] + rep + v[i+1:])
    return expanded

def score_similarity(a: str, b: str) -> float:
    """
    0~1 점수: 1에 가까울수록 동일
    Levenshtein distance를 길이로 정규화
    """
    a = normalize(a)
    b = normalize(b)
    if not a and not b:
        return 1.0
    dist = Levenshtein.distance(a, b)
    denom = max(len(a), len(b), 1)
    return 1.0 - (dist / denom)

def find_best_plate(ocr_text: str, parked_plates: list[str], top_k: int = 3):
    """
    DB(현재 주차중 번호판)에서 OCR과 가장 가까운 후보 찾기
    반환: best, best_score, top_candidates(list of (plate, score))
    """
    variants = generate_variants(ocr_text, max_edits=2)

    scored = {}
    for plate in parked_plates:
        best_for_plate = 0.0
        for v in variants:
            sc = score_similarity(v, plate)
            if sc > best_for_plate:
                best_for_plate = sc
        scored[plate] = best_for_plate

    top = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:top_k]
    best_plate, best_score = top[0] if top else (None, 0.0)
    return best_plate, float(best_score), [(p, float(s)) for p, s in top]
