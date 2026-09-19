import os
import re
import tkinter as tk
from tkinter import filedialog


def select_target_files() -> list:
    """폴더 선택 또는 파일 다중 선택 대화상자 (최상위 활성화 및 경로 직접 입력 지원)"""
    print("\n" + "=" * 60)
    print(" [파일 선택 방식]")
    print("  1. 폴더 선택창 열기 (창에서 폴더 선택) [기본값: Enter]")
    print("  2. 파일 선택창 열기 (창에서 파일 다중 선택)")
    print("  3. 폴더 경로 직접 입력 (콘솔에 경로 붙여넣기 / 현재 폴더: .)")
    print("=" * 60)
    choice = input("선택 번호를 입력하세요 (1/2/3, 기본값 1): ").strip()

    if choice == "3":
        folder_path = input("\n대상 폴더 경로를 입력하세요 (현재 폴더는 . 입력): ").strip().strip("\"'")
        if not folder_path:
            folder_path = "."
        if not os.path.isdir(folder_path):
            print(f"\n[오류] 올바른 폴더 경로가 아닙니다: {folder_path}")
            return []
        folder_path = os.path.abspath(folder_path)
        file_paths = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]
        file_paths.sort()
        return file_paths

    # GUI 창을 화면 맨 앞으로 띄우도록 설정
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    try:
        if choice == "2":
            print("\n파일 선택창을 여는 중입니다... (화면의 파일 선택창을 확인해 주세요)")
            file_paths = filedialog.askopenfilenames(
                parent=root,
                title="이름을 변경할 파일들을 선택하세요",
                filetypes=[
                    ("한글 문서", "*.hwp;*.hwpx"),
                    ("모든 파일", "*.*")
                ]
            )
            return list(file_paths)
        else:
            print("\n폴더 선택창을 여는 중입니다... (화면의 폴더 선택창을 확인해 주세요)")
            folder_path = filedialog.askdirectory(
                parent=root,
                title="이름을 변경할 파일들이 있는 폴더 선택"
            )
            if not folder_path:
                return []
            folder_path = os.path.abspath(folder_path)
            file_paths = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ]
            file_paths.sort()
            return file_paths
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def remove_copy_suffixes(filename: str) -> str:
    """윈도우 복사본 접미사('의 사본', '- 복사본', ' - Copy' 등) 완벽 제거"""
    # 1) '의 사본' (예: .hwp의 사본, 파일명_의 사본 등)
    name = re.sub(r"[\s._\-]*의\s*사본", "", filename)
    # 2) '- 복사본' 또는 ' - 복사본 (1)'
    name = re.sub(r"[\s._\-]*복사본(?:\s*\(\d+\))?", "", name)
    # 3) ' - Copy' 또는 ' Copy (1)'
    name = re.sub(r"[\s._\-]*Copy(?:\s*\(\d+\))?", "", name, flags=re.IGNORECASE)
    # 4) 확장자 앞 중복 공백 정리
    name = re.sub(r"\s+\.", ".", name).strip()
    return name


def standardize_mock_exam_date(name: str) -> str:
    """
    모의고사 및 시험지 파일명의 다양한 날짜 형식을 [YYYY-MM] 표준으로 자동 변환
    예: 2026년 9월 -> [2026-09]
        2025.06 -> [2025-06]
        2024-3 -> [2024-03]
    """
    # 1) '2024년 03월' 또는 '2024년 3월' 형태
    def repl_hangul(match):
        year, month = match.group(1), int(match.group(2))
        return f"[{year}-{month:02d}]"

    name = re.sub(r"(\d{4})년\s*(\d{1,2})월", repl_hangul, name)

    # 2) 대괄호 없이 '2024.03', '2024-03', '2024_03', '2024-3' 등 형태
    def repl_dot_dash(match):
        year, month = match.group(1), int(match.group(2))
        return f"[{year}-{month:02d}]"

    # [YYYY-MM] 이미 대괄호가 있는 경우는 제외하고 매칭 (_ 도 구분자로 처리)
    name = re.sub(r"(?<!\[)(?<!\d)(20\d{2})[._\-](\d{1,2})(?!\d)", repl_dot_dash, name)

    # 중복 공백 정리
    name = re.sub(r"\s+", " ", name).strip()
    return name


def plan_renaming(file_paths: list) -> list:
    """사용자가 선택한 규칙에 따라 변경 계획(old_path, new_name)을 생성"""
    print("\n" + "=" * 65)
    print(" [파일명 변경 규칙 선택]")
    print("  1. 윈도우 복사본 접미사 일괄 삭제 ('의 사본', '- 복사본' 등) [원클릭 추천] ⭐")
    print("  2. 특정 단어/기호 바꾸기 (찾아 바꾸기 / Replace)")
    print("  3. 접두사(맨 앞) 또는 접미사(맨 뒤) 추가")
    print("  4. 모의고사 날짜 형식 자동 표준화 (예: 2026년 9월 -> [2026-09])")
    print("  5. 정규표현식(Regex) 고급 치환")
    print("  6. 파일 순서대로 번호 매기기 (01_, 02_...)")
    print("=" * 65)

    mode = input("원하는 규칙 번호를 입력하세요 (1~6): ").strip()
    rename_plan = []

    if mode == "1":
        # 1. 윈도우 복사본 접미사 원클릭 삭제
        print("\n'의 사본', '- 복사본', ' - Copy' 등 윈도우 복사본 접미사를 일괄 제거합니다.")
        for path in file_paths:
            dirname, filename = os.path.split(path)
            new_name = remove_copy_suffixes(filename)
            rename_plan.append((path, new_name))

    elif mode == "2":
        # 2. 문자열 치환 (찾아 바꾸기)
        old_text = input("\n[찾을 문자열]: ")
        # 사용자가 따옴표로 감싸서 입력한 경우 따옴표 자동 제거
        if (old_text.startswith('"') and old_text.endswith('"')) or (old_text.startswith("'") and old_text.endswith("'")):
            if len(old_text) >= 2:
                old_text = old_text[1:-1]

        new_text = input("[바꿀 문자열 (삭제를 원하시면 빈칸으로 Enter)]: ")
        if (new_text.startswith('"') and new_text.endswith('"')) or (new_text.startswith("'") and new_text.endswith("'")):
            if len(new_text) >= 2:
                new_text = new_text[1:-1]

        for path in file_paths:
            dirname, filename = os.path.split(path)
            # 전체 파일명 대상 치환 (확장자 뒤에 붙은 '의 사본' 등도 완벽 치환)
            new_name = filename.replace(old_text, new_text)
            rename_plan.append((path, new_name))

    elif mode == "3":
        # 3. 접두사 / 접미사 추가
        prefix = input("\n[맨 앞에 추가할 텍스트 (없으면 Enter)]: ")
        suffix = input("[맨 뒤에 추가할 텍스트 (확장자 앞, 없으면 Enter)]: ")
        for path in file_paths:
            dirname, filename = os.path.split(path)
            name, ext = os.path.splitext(filename)
            new_name = f"{prefix}{name}{suffix}{ext}"
            rename_plan.append((path, new_name))

    elif mode == "4":
        # 4. 모의고사 날짜 자동 표준화
        print("\n모의고사 날짜 형식([YYYY-MM]) 자동 감지 및 변환을 적용합니다.")
        for path in file_paths:
            dirname, filename = os.path.split(path)
            name, ext = os.path.splitext(filename)
            converted_name = standardize_mock_exam_date(name)
            new_name = f"{converted_name}{ext}"
            rename_plan.append((path, new_name))

    elif mode == "5":
        # 5. 정규식 치환
        pattern = input("\n[찾을 정규표현식 패턴 (Regex)]: ")
        repl = input("[대체할 표현식 (예: \\1, \\2 등 사용 가능)]: ")
        regex = re.compile(pattern)
        for path in file_paths:
            dirname, filename = os.path.split(path)
            new_name = regex.sub(repl, filename)
            rename_plan.append((path, new_name))

    elif mode == "6":
        # 6. 번호 매기기
        prefix_str = input("\n[번호 뒤에 붙일 구분자 (기본값: '_ ')]: ")
        if not prefix_str:
            prefix_str = "_ "
        total_digits = len(str(len(file_paths)))
        if total_digits < 2:
            total_digits = 2

        for idx, path in enumerate(file_paths, 1):
            dirname, filename = os.path.split(path)
            new_name = f"{idx:0{total_digits}d}{prefix_str}{filename}"
            rename_plan.append((path, new_name))

    else:
        print("\n잘못된 선택입니다.")
        return []

    return rename_plan


def main():
    print("=" * 70)
    print(" [한글 문서 및 파일명 일괄 변경 도구 (Batch Renamer)] ")
    print("=" * 70)

    # 1. 대상 파일 선택
    file_paths = select_target_files()
    if not file_paths:
        print("\n선택된 파일이 없습니다. 프로그램을 종료합니다.")
        return

    print(f"\n총 {len(file_paths)}개의 파일이 선택되었습니다.")

    # 2. 변경 계획 수립
    rename_plan = plan_renaming(file_paths)
    if not rename_plan:
        return

    # 3. 변경 사항 미리보기 (Preview) 및 중복/충돌 검사
    print("\n" + "=" * 70)
    print(" [변경 미리보기 (Preview)] ")
    print("=" * 70)

    changes_count = 0
    valid_plan = []

    for old_path, new_name in rename_plan:
        dirname, old_name = os.path.split(old_path)
        new_path = os.path.join(dirname, new_name)

        if old_name != new_name:
            changes_count += 1
            print(f"  [변경] {old_name}")
            print(f"     ->  {new_name}")
            valid_plan.append((old_path, new_path, old_name, new_name))
        else:
            print(f"  [유지] {old_name} (변경 없음)")

    if changes_count == 0:
        print("\n변경될 파일명이 없습니다 (모든 파일명이 기존과 동일합니다). 프로그램을 종료합니다.")
        return

    print("=" * 70)
    print(f"총 {len(file_paths)}개 중 {changes_count}개의 파일명이 변경됩니다.")

    # 4. 사용자 최종 승인 확인 (안전장치)
    confirm = input("\n위와 같이 실제로 파일명을 변경하시겠습니까? (y/n, 기본값 y): ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("\n작업을 취소했습니다. 파일명이 변경되지 않았습니다.")
        return

    # 5. 실제 변경 실행
    print("\n파일명을 변경하는 중입니다...")
    success_count = 0
    error_count = 0

    for old_path, new_path, old_name, new_name in valid_plan:
        try:
            # 대상 파일이 이미 존재하는 경우 충돌 방지
            if os.path.exists(new_path) and os.path.abspath(old_path).lower() != os.path.abspath(new_path).lower():
                print(f"  [오류] 이미 존재하는 파일명입니다 (스킵): {new_name}")
                error_count += 1
                continue

            os.rename(old_path, new_path)
            success_count += 1
        except Exception as e:
            print(f"  [실패] {old_name} -> {e}")
            error_count += 1

    print("\n" + "=" * 60)
    print(" [변경 작업 완료] ")
    print(f"  - 성공: {success_count}개")
    if error_count > 0:
        print(f"  - 실패/스킵: {error_count}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
