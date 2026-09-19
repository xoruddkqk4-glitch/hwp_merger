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


def sanitize_text(text: str) -> str:
    """UTF-8 인코딩 불가능한 surrogate 문자 및 null 문자 정제"""
    if not text:
        return ""
    # 유라시아/특수기호/수식 등에서 발생하는 lone surrogate(\udb80 등) 제거
    cleaned = text.encode("utf-8", errors="ignore").decode("utf-8")
    return cleaned.replace("\x00", "").strip()


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
    initial_ext = ".hwpx" if any(f.lower().endswith(".hwpx") for f in file_list) else ".hwp"
    save_path = filedialog.asksaveasfilename(
        defaultextension=initial_ext,
        filetypes=[("HWPX 파일", "*.hwpx"), ("HWP 파일", "*.hwp")],
        initialfile=f"병합된_문서{initial_ext}",
        title="병합된 파일 저장 위치 지정"
    )

    if not save_path:
        print("\n저장을 취소했습니다. 프로그램을 종료합니다.")
        return

    save_path = os.path.abspath(save_path)
    txt_save_path = os.path.splitext(save_path)[0] + ".txt"

    # 3. 한글(pyhwpx) 인스턴스 초기화
    print("\n한글 인스턴스를 실행하는 중입니다...")
    hwpx = Hwp()
    hwp = hwpx.hwp

    try:
        # 4. [단계 1/2] 개별 문서 텍스트 추출 및 TXT 병합 (파일명 경계 구분)
        print("\n[단계 1/2] 초고속 검색용 TXT 병합 및 텍스트 추출 진행 중...")
        header_summary = (
            f"{'=' * 80}\n"
            f"[한글 문서 병합 텍스트 추출본]\n"
            f"- 생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- 병합 파일 수: {total_files}개\n"
            f"{'=' * 80}\n\n"
        )

        # errors="ignore"로 surrogate 오류 완벽 방지 및 실시간 디스크 기록
        with open(txt_save_path, "w", encoding="utf-8-sig", errors="ignore") as f_txt:
            f_txt.write(header_summary)

            for idx, file_path in enumerate(file_list, 1):
                filename = os.path.basename(file_path)
                print(f"  ({idx}/{total_files}) 텍스트 추출 중: {filename}")

                fmt = get_file_format(file_path)
                hwp.Open(file_path, fmt, "forceopen:true")

                # 문서 전체 텍스트 추출 및 lone surrogate 정제
                raw_content = hwpx.get_text_file("UNICODE", option="") or ""
                content = sanitize_text(raw_content)

                section_header = (
                    f"{'=' * 80}\n"
                    f"[{idx:02d}/{total_files:02d}] {filename}\n"
                    f"- 원본 경로: {file_path}\n"
                    f"{'=' * 80}\n\n"
                )
                f_txt.write(section_header)
                f_txt.write(content)
                f_txt.write("\n\n")
                f_txt.flush()

                hwp.Clear(1)  # 문서 닫기 및 변경사항 초기화

        print(f"  -> [완료] TXT 병합 파일 저장 완료: {txt_save_path}")

        # 5. [단계 2/2] 원본 서식 보존 HWP/HWPX 문서 병합
        print("\n[단계 2/2] 원본 서식 보존 HWP/HWPX 문서 병합 진행 중...")
        for idx, file_path in enumerate(file_list, 1):
            filename = os.path.basename(file_path)
            fmt = get_file_format(file_path)

            if idx == 1:
                print(f"  ({idx}/{total_files}) 기준 문서 오픈: {filename}")
                hwp.Open(file_path, fmt, "forceopen:true")
                hwp.MovePos(3, 0, 0)  # 문서 맨 끝으로 이동
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
                hwp.MovePos(3, 0, 0)      # 커서를 문서 맨 끝으로 이동

        # 최종 파일 저장 (HWP 또는 HWPX)
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
        print("모든 문서 병합 작업이 성공적으로 완료되었습니다!")
        print(f"1. 원본 서식 보존 병합 파일: {save_path}")
        print(f"2. 초고속 검색용 TXT 파일: {txt_save_path}")
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