import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from pyhwpx import Hwp


def select_files():
    root = tk.Tk()
    root.withdraw()  # Tk 창 숨기기
    file_paths = filedialog.askopenfilenames(
        title="HWP 또는 HWPX 파일 선택",
        filetypes=[
            ("한글 문서", "*.hwp;*.hwpx"),
            ("HWP 파일", "*.hwp"),
            ("HWPX 파일", "*.hwpx")
        ]
    )
    return list(file_paths)


def get_file_format(file_path: str) -> str:
    """파일 확장자에 따라 HWP / HWPX 포맷 문자열 반환"""
    return "HWPX" if file_path.lower().endswith(".hwpx") else "HWP"


def main():
    # 1. 병합할 파일 다중 선택
    file_list = select_files()
    if not file_list:
        print("파일을 선택하지 않았습니다. 프로그램을 종료합니다.")
        return

    total_files = len(file_list)
    print(f"\n[선택된 파일: 총 {total_files}개]")
    for idx, path in enumerate(file_list, 1):
        print(f"  {idx:02d}. {os.path.basename(path)}")

    # 2. 저장 위치 및 파일명 지정 (HWP/HWPX)
    save_path = filedialog.asksaveasfilename(
        defaultextension=".hwp",
        filetypes=[("HWP 파일", "*.hwp"), ("HWPX 파일", "*.hwpx")],
        initialfile="병합된_문서.hwp",
        title="병합된 파일 저장"
    )

    if not save_path:
        print("\n저장을 취소했습니다. 프로그램을 종료합니다.")
        return

    # TXT 파일 저장 경로 (동일 폴더 및 파일명에 .txt 확장자)
    txt_save_path = os.path.splitext(save_path)[0] + ".txt"

    # 3. 한글(pyhwpx) 인스턴스 초기화
    print("\n한글 인스턴스를 실행하는 중입니다...")
    hwpx = Hwp()
    hwp = hwpx.hwp

    try:
        # 4. [단계 1/2] 개별 문서 텍스트 추출 및 TXT 병합 (파일명 경계 구분)
        print("\n[단계 1/2] 초고속 검색용 TXT 병합 및 텍스트 추출 진행 중...")
        txt_sections = []

        header_summary = (
            f"{'=' * 80}\n"
            f"[한글 문서 병합 텍스트 추출본]\n"
            f"- 생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- 병합 파일 수: {total_files}개\n"
            f"{'=' * 80}\n\n"
        )
        txt_sections.append(header_summary)

        for idx, file_path in enumerate(file_list, 1):
            filename = os.path.basename(file_path)
            print(f"  ({idx}/{total_files}) 텍스트 추출 중: {filename}")

            fmt = get_file_format(file_path)
            hwp.Open(file_path, fmt, "forceopen:true")

            # 문서 전체 텍스트 추출
            content = hwpx.get_text_file("UNICODE", option="") or ""
            content = content.replace("\x00", "").strip()

            section_header = (
                f"{'=' * 80}\n"
                f"[{idx:02d}/{total_files:02d}] {filename}\n"
                f"- 원본 경로: {file_path}\n"
                f"{'=' * 80}\n\n"
            )
            txt_sections.append(f"{section_header}{content}\n\n")
            hwp.Clear(1)  # 문서 닫기 및 변경사항 초기화

        # TXT 파일 저장 (utf-8-sig 인코딩으로 메모장 및 엑셀 호환 보장)
        with open(txt_save_path, "w", encoding="utf-8-sig") as f:
            f.writelines(txt_sections)
        print(f"  -> TXT 병합 파일 저장 완료: {txt_save_path}")

        # 5. [단계 2/2] 서식 보존 HWP 문서 병합 진행
        print("\n[단계 2/2] 원본 서식 보존 HWP 문서 병합 진행 중...")
        for idx, file_path in enumerate(file_list, 1):
            filename = os.path.basename(file_path)
            fmt = get_file_format(file_path)

            if idx == 1:
                print(f"  ({idx}/{total_files}) 기준 문서 오픈: {filename}")
                hwp.Open(file_path, fmt, "forceopen:true")
                hwp.MovePos(3, 0, 0)  # 문서의 맨 끝으로 이동
            else:
                print(f"  ({idx}/{total_files}) 문서 끼워넣기: {filename}")
                hwp.HAction.GetDefault("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                option = hwp.HParameterSet.HInsertFile
                option.filename = file_path
                option.KeepSection = 1    # 쪽 모양 유지
                option.KeepCharshape = 1  # 글자 모양 유지
                option.KeepParashape = 1  # 문단 모양 유지
                option.KeepStyle = 1      # 스타일 유지
                hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                hwp.MovePos(3, 0, 0)      # 커서를 문서의 맨 끝으로 이동

        # HWP 파일 저장
        save_format = get_file_format(save_path)
        hwp.HAction.GetDefault("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)
        save_option = hwp.HParameterSet.HFileOpenSave
        save_option.Attributes = 0
        save_option.filename = save_path
        save_option.Format = save_format
        hwp.HAction.Execute("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)

        print("\n" + "=" * 60)
        print("모든 문서 병합 작업이 성공적으로 완료되었습니다!")
        print(f"1. 서식 보존 HWP 병합 파일: {save_path}")
        print(f"2. 초고속 검색용 TXT 병합 파일: {txt_save_path}")
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