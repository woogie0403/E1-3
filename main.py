"""Mini NPU Simulator: MAC 연산 기반 패턴 판별 및 성능 분석 콘솔 애플리케이션."""


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
