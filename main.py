"""Mini NPU Simulator: MAC 연산 기반 패턴 판별 및 성능 분석 콘솔 애플리케이션."""

import math
import time
from typing import List, Optional, Tuple

EPSILON = 1e-9
DEFAULT_BENCHMARK_REPEAT = 10


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


def run_json_analysis_mode() -> None:
    """모드 2: data.json 분석 실행 자리 (STEP 5에서 구현 예정)."""
    print("\n[안내] 모드 2(data.json 분석)가 선택되었습니다. (STEP 5에서 구현 예정)")


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
