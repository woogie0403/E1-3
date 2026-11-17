"""Mini NPU Simulator: MAC 연산 기반 패턴 판별 및 성능 분석 콘솔 애플리케이션."""

import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EPSILON = 1e-9
DEFAULT_BENCHMARK_REPEAT = 10

LABEL_CROSS = "Cross"
LABEL_X = "X"
LABEL_UNDECIDED = "UNDECIDED"
LABEL_ALIASES = {
    "+": LABEL_CROSS,
    "cross": LABEL_CROSS,
    "x": LABEL_X,
}
DATA_FILE_PATH = Path(__file__).resolve().parent / "data.json"


def is_valid_square_matrix(matrix: object, expected_size: Optional[int] = None) -> bool:
    """입력이 N×N 정방 숫자 행렬인지(선택적으로 expected_size 일치 여부 포함) 검증한다."""
    if not isinstance(matrix, list) or len(matrix) == 0:
        return False

    size = len(matrix)
    if expected_size is not None and size != expected_size:
        return False

    for row in matrix:
        if not isinstance(row, list) or len(row) != size:
            return False
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False
            if not math.isfinite(value):
                return False

    return True


def compute_mac(pattern: List[List[float]], flt: List[List[float]]) -> float:
    """외부 라이브러리 없이 이중 반복문으로 N×N 패턴과 필터의 MAC 연산 점수를 계산한다."""
    if not is_valid_square_matrix(pattern):
        raise ValueError("패턴이 유효한 N×N 정방 숫자 행렬이 아닙니다.")

    size = len(pattern)
    if not is_valid_square_matrix(flt, expected_size=size):
        raise ValueError(
            f"필터가 유효하지 않거나 패턴 크기({size}×{size})와 일치하지 않습니다."
        )

    total = 0.0
    for row in range(size):
        for col in range(size):
            total += pattern[row][col] * flt[row][col]
    return total


def judge_scores(
    score_a: float,
    score_b: float,
    label_a: str = "A",
    label_b: str = "B",
    tie_label: str = "UNDECIDED",
    epsilon: float = EPSILON,
) -> str:
    """허용오차(epsilon) 기반 정책으로 두 필터 점수를 비교해 최종 라벨을 판정한다."""
    if abs(score_a - score_b) < epsilon:
        return tie_label
    if score_a > score_b:
        return label_a
    return label_b


def benchmark_mac(
    pattern: List[List[float]],
    flt: List[List[float]],
    repeat: int = DEFAULT_BENCHMARK_REPEAT,
) -> Tuple[float, int]:
    """I/O를 제외한 순수 compute_mac 호출 구간을 repeat회 반복 측정해 (평균 ms, 연산 횟수 N^2)를 반환한다."""
    if repeat < 1:
        raise ValueError("반복 측정 횟수는 1 이상이어야 합니다.")

    # 측정 구간 밖에서 사전 검증 및 1회 워밍업을 수행한다.
    compute_mac(pattern, flt)
    size = len(pattern)
    op_count = size * size

    start = time.perf_counter()
    for _ in range(repeat):
        compute_mac(pattern, flt)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    avg_ms = elapsed_ms / repeat
    return avg_ms, op_count


def create_benchmark_matrices(size: int) -> Tuple[List[List[float]], List[List[float]]]:
    """성능 측정을 위해 N×N 십자가 형태의 테스트 패턴과 필터 한 쌍을 생성한다."""
    if size < 1:
        raise ValueError("행렬 크기는 1 이상이어야 합니다.")

    mid = size // 2
    pattern = [
        [1.0 if (r == mid or c == mid) else 0.0 for c in range(size)]
        for r in range(size)
    ]
    flt = [row[:] for row in pattern]
    return pattern, flt


def measure_sizes(
    size_pairs: List[Tuple[int, List[List[float]], List[List[float]]]],
    repeat: int = DEFAULT_BENCHMARK_REPEAT,
) -> List[Tuple[int, float, int]]:
    """여러 크기의 (N, 패턴, 필터) 목록에 대해 순수 연산 시간만 측정해 결과 리스트를 반환한다."""
    results: List[Tuple[int, float, int]] = []
    for size, pattern, flt in size_pairs:
        avg_ms, op_count = benchmark_mac(pattern, flt, repeat=repeat)
        results.append((size, avg_ms, op_count))
    return results


def print_performance_table(
    results: List[Tuple[int, float, int]],
    repeat: int = DEFAULT_BENCHMARK_REPEAT,
) -> None:
    """크기별 평균 MAC 연산 시간(ms)과 연산 횟수(N^2) 표를 출력한다."""
    print("#---------------------------------------")
    print(f"# [3] 성능 분석 (평균/{repeat}회)")
    print("#---------------------------------------")
    print(f"{'크기':<8} {'평균 시간(ms)':>13} {'연산 횟수':>10}")
    print("-" * 37)
    for size, avg_ms, op_count in results:
        size_label = f"{size}×{size}"
        print(f"{size_label:<8} {avg_ms:>13.4f} {op_count:>10}")


def select_mode() -> str:
    """사용자로부터 실행할 모드('1' 또는 '2')를 안전하게 입력받는다."""
    print("=== Mini NPU Simulator ===")
    print()
    print("[모드 선택]")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")

    while True:
        choice = input("선택: ").strip()
        if choice in ("1", "2"):
            return choice
        print("입력 오류: 1 또는 2를 입력하세요.")


def parse_matrix_row(line: str, expected_cols: int = 3) -> List[float]:
    """공백으로 구분된 한 줄 문자열을 파싱해 길이 expected_cols의 유한 실수 리스트로 반환한다."""
    tokens = line.strip().split()
    if len(tokens) != expected_cols:
        raise ValueError(
            f"입력 형식 오류: 각 줄에 {expected_cols}개의 숫자를 공백으로 구분해 입력하세요."
        )

    row: List[float] = []
    for token in tokens:
        try:
            value = float(token)
        except ValueError as exc:
            raise ValueError(
                f"입력 형식 오류: 각 줄에 {expected_cols}개의 숫자를 공백으로 구분해 입력하세요."
            ) from exc
        if not math.isfinite(value):
            raise ValueError(
                f"입력 형식 오류: 각 줄에 {expected_cols}개의 숫자를 공백으로 구분해 입력하세요."
            )
        row.append(value)
    return row


def read_square_matrix(name: str, size: int = 3) -> List[List[float]]:
    """콘솔에서 size줄의 공백 구분 숫자 입력을 받아 size×size 2차원 리스트로 반환한다."""
    print(f"{name} ({size}줄 입력, 공백 구분)")
    matrix: List[List[float]] = []
    for row_idx in range(size):
        while True:
            raw_line = input()
            try:
                row = parse_matrix_row(raw_line, expected_cols=size)
                matrix.append(row)
                break
            except ValueError as exc:
                print(f"{exc} ({row_idx + 1}번째 줄 재입력)")
    return matrix


def run_user_input_mode() -> None:
    """모드 1: 사용자 입력(3x3) 필터 A, B와 패턴을 입력받아 MAC 연산·판정·성능을 출력한다."""
    print("\n#---------------------------------------")
    print("# [1] 필터 입력")
    print("#---------------------------------------")
    filter_a = read_square_matrix("필터 A", size=3)
    print()
    filter_b = read_square_matrix("필터 B", size=3)
    print("\n✓ 필터 A, B (3×3) 저장 확인 완료")

    print("\n#---------------------------------------")
    print("# [2] 패턴 입력")
    print("#---------------------------------------")
    pattern = read_square_matrix("패턴", size=3)

    score_a = compute_mac(pattern, filter_a)
    score_b = compute_mac(pattern, filter_b)
    avg_ms, op_count = benchmark_mac(pattern, filter_a, repeat=DEFAULT_BENCHMARK_REPEAT)
    verdict = judge_scores(
        score_a, score_b, label_a="A", label_b="B", tie_label="판정 불가"
    )

    print("\n#---------------------------------------")
    print("# [3] MAC 결과")
    print("#---------------------------------------")
    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"연산 시간(평균/{DEFAULT_BENCHMARK_REPEAT}회): {avg_ms:.4f} ms")
    if verdict == "판정 불가":
        print("판정: 판정 불가 (|A-B| < 1e-9)")
    else:
        print(f"판정: {verdict}")

    print()
    print_performance_table([(3, avg_ms, op_count)], repeat=DEFAULT_BENCHMARK_REPEAT)


def normalize_label(raw_label: object) -> str:
    """다양한 입력 라벨('+', 'cross', 'x' 등)을 표준 라벨('Cross', 'X')로 정규화한다."""
    if not isinstance(raw_label, str):
        raise ValueError(f"라벨은 문자열이어야 합니다: {raw_label!r}")

    key = raw_label.strip().lower()
    if key not in LABEL_ALIASES:
        raise ValueError(f"지원하지 않는 라벨입니다: {raw_label!r}")
    return LABEL_ALIASES[key]


def parse_size_key(key: str, expected_parts: int) -> int:
    """'size_{N}'(2부분) 또는 'size_{N}_{idx}'(3부분) 키에서 정수 N을 추출한다."""
    if not isinstance(key, str):
        raise ValueError(f"키는 문자열이어야 합니다: {key!r}")

    parts = key.split("_", expected_parts - 1)
    if len(parts) != expected_parts or parts[0] != "size" or not parts[1].isdigit():
        raise ValueError(f"키 형식이 올바르지 않습니다: {key!r}")

    size = int(parts[1])
    if size < 1:
        raise ValueError(f"크기 N은 1 이상이어야 합니다: {key!r}")
    return size


def load_json_data(filepath: Path = DATA_FILE_PATH) -> Optional[Dict[str, Any]]:
    """JSON 파일을 안전하게 읽어 최상위 딕셔너리를 반환한다. 오류 시 안내 후 None을 반환한다."""
    try:
        with filepath.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"[오류] 데이터 파일을 찾을 수 없습니다: {filepath}")
        return None
    except json.JSONDecodeError as exc:
        print(f"[오류] JSON 문법이 올바르지 않습니다 ({filepath.name}): {exc}")
        return None
    except OSError as exc:
        print(f"[오류] 파일을 읽는 중 문제가 발생했습니다: {exc}")
        return None

    if not isinstance(data, dict):
        print("[오류] JSON 최상위 구조는 객체(dict)여야 합니다.")
        return None
    return data


def load_normalized_filters(
    filters_raw: object,
) -> Dict[int, Dict[str, List[List[float]]]]:
    """data.json의 filters 섹션을 읽어 크기별 표준 라벨('Cross', 'X') 필터 딕셔너리로 반환한다."""
    normalized: Dict[int, Dict[str, List[List[float]]]] = {}
    if not isinstance(filters_raw, dict):
        print("[오류] 'filters' 항목이 없거나 딕셔너리 형식이 아닙니다.")
        return normalized

    print("\n#---------------------------------------")
    print("# [1] 필터 로드")
    print("#---------------------------------------")
    for filter_key, filter_group in filters_raw.items():
        try:
            size = parse_size_key(filter_key, expected_parts=2)
        except ValueError as exc:
            print(f"✗ 필터 키 오류({filter_key}): {exc}")
            continue

        if not isinstance(filter_group, dict):
            print(f"✗ {filter_key} 필터 구조 오류: 딕셔너리가 아닙니다.")
            continue

        size_filters: Dict[str, List[List[float]]] = {}
        for raw_label, matrix in filter_group.items():
            try:
                std_label = normalize_label(raw_label)
            except ValueError as exc:
                print(f"✗ {filter_key} 라벨 오류: {exc}")
                continue
            if not is_valid_square_matrix(matrix, expected_size=size):
                print(f"✗ {filter_key}({std_label}) 행렬 크기/형식 오류 (기대: {size}×{size})")
                continue
            size_filters[std_label] = matrix

        if LABEL_CROSS in size_filters and LABEL_X in size_filters:
            normalized[size] = size_filters
            print(f"✓ {filter_key} 필터 로드 완료 ({LABEL_CROSS}, {LABEL_X})")
        else:
            print(f"✗ {filter_key} 필터 불완전: {LABEL_CROSS}/{LABEL_X} 중 일부가 누락/오류")

    return normalized


def evaluate_pattern_case(
    case_id: str,
    entry: object,
    filters_by_size: Dict[int, Dict[str, List[List[float]]]],
) -> Dict[str, Any]:
    """단일 패턴 케이스를 검증·계산·판정하며, 오류가 발생해도 예외를 격리해 FAIL 결과를 반환한다."""
    try:
        size = parse_size_key(case_id, expected_parts=3)
    except ValueError as exc:
        return {"case_id": case_id, "passed": False, "reason": f"키/스키마 오류: {exc}"}

    if not isinstance(entry, dict):
        return {"case_id": case_id, "passed": False, "reason": "스키마 오류: 케이스 항목이 dict가 아님"}

    if "input" not in entry or "expected" not in entry:
        return {"case_id": case_id, "passed": False, "reason": "스키마 오류: input 또는 expected 누락"}

    try:
        expected_label = normalize_label(entry["expected"])
    except ValueError as exc:
        return {"case_id": case_id, "passed": False, "reason": f"expected 라벨 오류: {exc}"}

    size_filters = filters_by_size.get(size)
    if not size_filters or LABEL_CROSS not in size_filters or LABEL_X not in size_filters:
        return {"case_id": case_id, "passed": False, "reason": f"size_{size} 필터 없음 또는 로드 실패"}

    pattern_matrix = entry["input"]
    if not is_valid_square_matrix(pattern_matrix, expected_size=size):
        return {
            "case_id": case_id,
            "passed": False,
            "reason": f"크기/형식 불일치: 기대 크기 {size}×{size}",
        }

    score_cross = compute_mac(pattern_matrix, size_filters[LABEL_CROSS])
    score_x = compute_mac(pattern_matrix, size_filters[LABEL_X])
    verdict = judge_scores(
        score_cross,
        score_x,
        label_a=LABEL_CROSS,
        label_b=LABEL_X,
        tie_label=LABEL_UNDECIDED,
    )

    passed = verdict == expected_label
    reason = ""
    if not passed:
        if verdict == LABEL_UNDECIDED:
            reason = f"동점({LABEL_UNDECIDED}) 처리 규칙에 따라 FAIL (|Cross-X| < {EPSILON})"
        else:
            reason = f"판정 불일치 (예상: {expected_label}, 판정: {verdict})"

    return {
        "case_id": case_id,
        "size": size,
        "pattern": pattern_matrix,
        "score_cross": score_cross,
        "score_x": score_x,
        "verdict": verdict,
        "expected": expected_label,
        "passed": passed,
        "reason": reason,
    }


def build_mode2_benchmark_pairs(
    filters_by_size: Dict[int, Dict[str, List[List[float]]]],
    case_results: List[Dict[str, Any]],
) -> List[Tuple[int, List[List[float]], List[List[float]]]]:
    """성능 분석용 (3×3 포함, 5×5/13×13/25×25) 패턴·필터 쌍을 구성한다."""
    valid_patterns_by_size: Dict[int, List[List[float]]] = {}
    for result in case_results:
        size = result.get("size")
        pattern = result.get("pattern")
        if isinstance(size, int) and pattern is not None and size not in valid_patterns_by_size:
            valid_patterns_by_size[size] = pattern

    pairs: List[Tuple[int, List[List[float]], List[List[float]]]] = []
    for target_size in (3, 5, 13, 25):
        if target_size in filters_by_size and target_size in valid_patterns_by_size:
            pairs.append(
                (
                    target_size,
                    valid_patterns_by_size[target_size],
                    filters_by_size[target_size][LABEL_CROSS],
                )
            )
        else:
            sample_pattern, sample_filter = create_benchmark_matrices(target_size)
            pairs.append((target_size, sample_pattern, sample_filter))
    return pairs


def run_json_analysis_mode(filepath: Path = DATA_FILE_PATH) -> None:
    """모드 2: data.json을 로드해 라벨 정규화·검증·MAC 판정·성능 분석·결과 요약을 출력한다."""
    data = load_json_data(filepath)
    if data is None:
        return

    filters_by_size = load_normalized_filters(data.get("filters"))
    patterns_raw = data.get("patterns")
    if not isinstance(patterns_raw, dict):
        print("\n[오류] 'patterns' 항목이 없거나 딕셔너리 형식이 아닙니다.")
        return

    print("\n#---------------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#---------------------------------------")

    case_results: List[Dict[str, Any]] = []
    for case_id, entry in patterns_raw.items():
        result = evaluate_pattern_case(case_id, entry, filters_by_size)
        case_results.append(result)

        print(f"--- {case_id} ---")
        if "score_cross" in result:
            print(f"Cross 점수: {result['score_cross']}")
            print(f"X 점수: {result['score_x']}")
            status = "PASS" if result["passed"] else "FAIL"
            extra = " (동점 규칙)" if result["verdict"] == LABEL_UNDECIDED and not result["passed"] else ""
            print(f"판정: {result['verdict']} | expected: {result['expected']} | {status}{extra}")
        else:
            print(f"판정: ERROR | FAIL ({result['reason']})")

    benchmark_pairs = build_mode2_benchmark_pairs(filters_by_size, case_results)
    perf_results = measure_sizes(benchmark_pairs, repeat=DEFAULT_BENCHMARK_REPEAT)
    print()
    print_performance_table(perf_results, repeat=DEFAULT_BENCHMARK_REPEAT)

    total_count = len(case_results)
    passed_count = sum(1 for item in case_results if item["passed"])
    failed_items = [item for item in case_results if not item["passed"]]

    print("\n#---------------------------------------")
    print("# [4] 결과 요약")
    print("#---------------------------------------")
    print(f"총 테스트: {total_count}개")
    print(f"통과: {passed_count}개")
    print(f"실패: {len(failed_items)}개")
    print()
    if failed_items:
        print("실패 케이스:")
        for item in failed_items:
            print(f"- {item['case_id']}: {item['reason']}")
    else:
        print("실패 케이스: 없음")


def main() -> None:
    """프로그램 메인 진입점."""
    try:
        mode = select_mode()
        if mode == "1":
            run_user_input_mode()
        elif mode == "2":
            run_json_analysis_mode()
    except (KeyboardInterrupt, EOFError):
        print("\n[안내] 사용자 요청 또는 입력 종료로 프로그램을 안전하게 종료합니다.")


if __name__ == "__main__":
    main()
