"""Mini NPU Simulator: MAC 연산 기반 패턴 판별 및 성능 분석 콘솔 애플리케이션."""

import math
from typing import List, Optional

EPSILON = 1e-9


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


def run_user_input_mode() -> None:
    """모드 1: 사용자 입력(3x3) 실행 자리 (STEP 4에서 구현 예정)."""
    print("\n[안내] 모드 1(사용자 입력 3x3)이 선택되었습니다. (STEP 4에서 구현 예정)")


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
