import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from pyhwpx import Hwp


def select_base_file() -> str:
    """기존에 병합된 대용량 파일 선택"""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="[1단계] 기존에 병합된 대용량 파일(HWP/HWPX) 선택",
        filetypes=[
            ("한글 문서", "*.hwp;*.hwpx"),
            ("HWPX 파일", "*.hwpx"),
            ("HWP 파일", "*.hwp")
        ]
    )
    return file_path


def select_new_files() -> list:
    """맨 앞에 최신순으로 추가할 신규 파일들 선택"""
    root = tk.Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="[2단계] 맨 앞에 추가할 신규 파일 선택 (다중 선택 가능)",
        filetypes=[
            ("한글 문서", "*.hwp;*.hwpx"),
            ("HWPX 파일", "*.hwpx"),
            ("HWP 파일", "*.hwp")
        ]
    )
    return list(file_paths)


def select_save_path(base_file: str) -> str:
    """결과물 저장 경로 지정 (기본값: 원본파일명_최신추가)"""
    root = tk.Tk()
    root.withdraw()
    base_dir = os.path.dirname(base_file)
    base_name = os.path.basename(base_file)
    name_without_ext, ext = os.path.splitext(base_name)
    initial_name = f"{name_without_ext}_최신추가{ext}"

    file_path = filedialog.asksaveasfilename(
        initialdir=base_dir,
        initialfile=initial_name,
        title="[3단계] 병합 결과를 저장할 파일 지정 (기존 파일 선택 시 덮어쓰기)",
        defaultextension=ext,
        filetypes=[
            ("동일 형식", f"*{ext}"),
            ("HWPX 파일", "*.hwpx"),
            ("HWP 파일", "*.hwp")
        ]
    )
    return file_path


def get_file_format(file_path: str) -> str:
    """파일 확장자에 따라 HWP / HWPX 포맷 문자열 반환"""
    return "HWPX" if file_path.lower().endswith(".hwpx") else "HWP"


def sanitize_text(text: str) -> str:
    """UTF-8 인코딩 불가능한 surrogate 문자 및 null 문자 정제"""
    if not text:
        return ""
    cleaned = text.encode("utf-8", errors="ignore").decode("utf-8")
    return cleaned.replace("\x00", "").strip()


def main():
    print("=" * 70)
    print(" [최신순 맨 앞 증분 병합 도구] ")
    print(" 기존 대용량 병합본 앞에 신규 파일(들)을 최신순으로 초고속 결합합니다.")
    print("=" * 70)

    # 1. 기존 병합 파일 선택
    base_file = select_base_file()
    if not base_file:
        print("\n기존 병합 파일을 선택하지 않았습니다. 프로그램을 종료합니다.")
        return
    base_file = os.path.abspath(base_file)
    print(f"\n[기존 병합 파일]: {os.path.basename(base_file)}")

    # 2. 신규 파일(들) 선택
    new_files = select_new_files()
    if not new_files:
        print("\n추가할 신규 파일을 선택하지 않았습니다. 프로그램을 종료합니다.")
        return

    total_new = len(new_files)
    print(f"\n[맨 앞에 추가할 신규 파일: 총 {total_new}개]")
    for idx, path in enumerate(new_files, 1):
        print(f"  {idx:02d}. {os.path.basename(path)}")

    # 3. 저장 위치 지정
    save_path = select_save_path(base_file)
    if not save_path:
        print("\n저장 위치를 선택하지 않았습니다. 프로그램을 종료합니다.")
        return

    save_path = os.path.abspath(save_path)
    if save_path.lower().endswith(".hwpx.hwpx"):
        save_path = save_path[:-5]
    elif save_path.lower().endswith(".hwp.hwp"):
        save_path = save_path[:-4]

    txt_save_path = os.path.splitext(save_path)[0] + ".txt"
    base_txt_path = os.path.splitext(base_file)[0] + ".txt"

    # 4. 한글 인스턴스 초기화 (화면 렌더링 끄기 - 초고속 백그라운드 모드)
    print("\n한글 인스턴스를 백그라운드(화면 렌더링 끄기 / 초고속 모드)로 실행하는 중입니다...")
    hwpx = Hwp(new=True, visible=False)
    hwp = hwpx.hwp
    hwp.SetMessageBoxMode(0x00020000)  # 무인 자동화 모드: 불필요한 알림/팝업창 억제

    try:
        # -------------------------------------------------------------
        # [단계 1/2] 초고속 검색용 TXT 병합 (신규 파일 텍스트를 맨 앞에 결합)
        # -------------------------------------------------------------
        print("\n[단계 1/2] 초고속 검색용 TXT 파일 증분 병합 진행 중...")
        new_txt_sections = []

        header_summary = (
            f"{'=' * 80}\n"
            f"[한글 문서 증분 병합 텍스트 (최신 파일 맨 앞 추가)]\n"
            f"- 추가 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- 신규 추가 파일 수: {total_new}개\n"
            f"{'=' * 80}\n\n"
        )
        new_txt_sections.append(header_summary)

        # 신규 파일들의 텍스트 추출
        for idx, file_path in enumerate(new_files, 1):
            filename = os.path.basename(file_path)
            print(f"  - 신규 파일 텍스트 추출 ({idx}/{total_new}): {filename}")

            fmt = get_file_format(file_path)
            hwp.Open(file_path, fmt, "forceopen:true")

            raw_content = hwpx.get_text_file("UNICODE", option="") or ""
            content = sanitize_text(raw_content)

            section_header = (
                f"{'=' * 80}\n"
                f"[신규 추가 {idx:02d}/{total_new:02d}] {filename}\n"
                f"- 원본 경로: {file_path}\n"
                f"{'=' * 80}\n\n"
            )
            new_txt_sections.append(f"{section_header}{content}\n\n")
            hwp.Clear(1)

        # 기존 TXT 파일 내용 읽기
        existing_txt = ""
        if os.path.exists(base_txt_path):
            try:
                with open(base_txt_path, "r", encoding="utf-8-sig", errors="ignore") as f_old:
                    existing_txt = f_old.read()
                print(f"  - 기존 TXT 파일({os.path.basename(base_txt_path)}) 내용 결합 완료")
            except Exception as read_err:
                print(f"  [주의] 기존 TXT 파일 읽기 실패: {read_err}")

        # 신규 텍스트 + 기존 텍스트 순서로 저장
        with open(txt_save_path, "w", encoding="utf-8-sig", errors="ignore") as f_txt:
            f_txt.writelines(new_txt_sections)
            if existing_txt:
                f_txt.write(f"\n\n{'#' * 80}\n# [기존 통합 문서 내용 이어짐]\n{'#' * 80}\n\n")
                f_txt.write(existing_txt)

        print(f"  -> [완료] TXT 병합 파일 저장 완료: {txt_save_path}")

        # -------------------------------------------------------------
        # [단계 2/2] 원본 서식 보존 HWP/HWPX 문서 증분 병합
        # (원리: 신규 파일 오픈 -> 기존 대용량 병합본을 1회만 InsertFile)
        # -------------------------------------------------------------
        print("\n[단계 2/2] 원본 서식 보존 HWP/HWPX 문서 증분 병합 진행 중...")

        # 1) 첫 번째 신규 파일 열기
        first_new = new_files[0]
        fmt_first = get_file_format(first_new)
        print(f"  - 첫 번째 신규 기준 문서 오픈: {os.path.basename(first_new)}")
        hwp.Open(first_new, fmt_first, "forceopen:true")
        hwp.MovePos(3, 0, 0)

        # 2) 나머지 신규 파일들이 있다면 순서대로 끼워넣기
        for file_path in new_files[1:]:
            filename = os.path.basename(file_path)
            print(f"  - 다음 신규 문서 끼워넣기: {filename}")
            hwp.HAction.GetDefault("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
            option = hwp.HParameterSet.HInsertFile
            option.filename = file_path
            option.KeepSection = 1
            option.KeepCharshape = 1
            option.KeepParashape = 1
            option.KeepStyle = 1
            hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
            hwp.MovePos(3, 0, 0)

        # 3) 신규 파일들 맨 뒤에 '기존 대용량 병합 파일'을 단 1회 InsertFile!
        print(f"  - 기존 대용량 병합본 단 1회 결합 중: {os.path.basename(base_file)}...")
        hwp.HAction.GetDefault("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
        option = hwp.HParameterSet.HInsertFile
        option.filename = base_file
        option.KeepSection = 1
        option.KeepCharshape = 1
        option.KeepParashape = 1
        option.KeepStyle = 1
        hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
        hwp.MovePos(3, 0, 0)

        # 4) 최종 파일 저장
        save_format = get_file_format(save_path)
        print(f"\n병합된 문서를 {save_format} 포맷으로 저장 중입니다: {save_path}")
        hwp.HAction.GetDefault("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)
        save_option = hwp.HParameterSet.HFileOpenSave
        save_option.Attributes = 0
        save_option.filename = save_path
        save_option.Format = save_format
        hwp.HAction.Execute("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)
        print(f"  -> [완료] {save_format} 병합 파일 저장 완료: {save_path}")

        print("\n" + "=" * 60)
        print("최신순 증분 병합이 단 몇 초 만에 완료되었습니다!")
        print(f"1. 최신순 HWP/HWPX 파일: {save_path}")
        print(f"2. 최신순 검색용 TXT 파일: {txt_save_path}")
        print("=" * 60)

    except Exception as e:
        print(f"\n[오류 발생] 병합 중 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()

    finally:
        try:
            hwp.Quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
