import os
import re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from pyhwpx import Hwp


def select_merged_document() -> tuple:
    """전체 병합 문서(.txt 또는 .hwpx/.hwp) 선택 및 관련 파일 경로 반환"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    try:
        selected_file = filedialog.askopenfilename(
            parent=root,
            title="[1단계] 전체 병합 문서(.txt 또는 .hwpx/.hwp) 선택",
            filetypes=[
                ("병합 파일 (TXT / HWPX / HWP)", "*.txt;*.hwpx;*.hwp"),
                ("텍스트 파일", "*.txt"),
                ("HWPX 파일", "*.hwpx"),
                ("HWP 파일", "*.hwp"),
                ("모든 파일", "*.*")
            ]
        )
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    if not selected_file:
        return "", ""

    selected_file = os.path.abspath(selected_file)
    ext = os.path.splitext(selected_file)[1].lower()

    if ext == ".txt":
        txt_path = selected_file
        # 같은 폴더에 대응하는 hwpx 또는 hwp가 있는지 확인
        base_no_ext = os.path.splitext(selected_file)[0]
        hwpx_candidate = base_no_ext + ".hwpx"
        hwp_candidate = base_no_ext + ".hwp"
        merged_doc_path = (
            hwpx_candidate if os.path.exists(hwpx_candidate)
            else (hwp_candidate if os.path.exists(hwp_candidate) else "")
        )
    else:
        merged_doc_path = selected_file
        # 동일 폴더의 .txt 파일 탐색
        txt_candidate = os.path.splitext(selected_file)[0] + ".txt"
        if os.path.exists(txt_candidate):
            txt_path = txt_candidate
        else:
            print(f"\n[안내] 선택하신 파일과 동일한 이름의 텍스트 파일({os.path.basename(txt_candidate)})을 찾을 수 없습니다.")
            print("문서 목록 및 경로 정보가 담긴 .txt 파일을 직접 선택해 주세요.")
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                txt_path = filedialog.askopenfilename(
                    parent=root,
                    title="병합 텍스트(.txt) 파일 선택",
                    filetypes=[("텍스트 파일", "*.txt")]
                )
            finally:
                try:
                    root.destroy()
                except Exception:
                    pass

    return txt_path, merged_doc_path


def parse_merged_txt(txt_path: str) -> list:
    """
    병합된 TXT 파일에서 각 문서의 [파일명, 원본 경로, 날짜(YYYY-MM), 텍스트 블록] 추출
    """
    with open(txt_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        content = f.read()

    # 문서별 헤더 패턴 매칭
    pattern = r"={40,}\s*\n\[\s*(\d+)/(\d+)\s*\]\s*([^\n]+)\n-\s*원본 경로:\s*([^\n]+)\n={40,}"
    matches = list(re.finditer(pattern, content))

    if not matches:
        # 혹시 [/] 형태가 아니라 [번호] 형태일 경우도 대비
        pattern = r"={40,}\s*\n\[\s*(\d+)\s*\]\s*([^\n]+)\n-\s*원본 경로:\s*([^\n]+)\n={40,}"
        matches = list(re.finditer(pattern, content))

    parsed_docs = []

    for idx, m in enumerate(matches):
        if len(m.groups()) == 4:
            curr_idx, total_count, filename, filepath = m.groups()
        else:
            curr_idx, filename, filepath = m.groups()

        filename = filename.strip()
        filepath = filepath.strip()

        # 문서 블록 범위 산출
        start_pos = m.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        block_text = content[start_pos:end_pos].strip()

        # 날짜 추출 (YYYY-MM 형식)
        doc_date = extract_date_from_name(filename)

        parsed_docs.append({
            "index": int(curr_idx) if curr_idx.isdigit() else idx + 1,
            "filename": filename,
            "filepath": filepath,
            "date": doc_date,
            "block_text": block_text
        })

    return parsed_docs


def extract_date_from_name(filename: str) -> str:
    """파일명에서 YYYY-MM 형식의 날짜 추출"""
    # 1) [YYYY-MM] 또는 [YYYY-MM-DD]
    m = re.search(r"\[(\d{4})[-._](\d{1,2})", filename)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    # 2) YYYY-MM 또는 YYYY.MM (대괄호 없음)
    m = re.search(r"(?<!\d)(20\d{2}|19\d{2})[-._](\d{1,2})", filename)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    # 3) YYYY년 MM월
    m = re.search(r"(\d{4})년\s*(\d{1,2})월", filename)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    # 4) 단순 4자리 연도만 있는 경우
    m = re.search(r"\b(20\d{2}|19\d{2})\b", filename)
    if m:
        return f"{m.group(1)}-01"

    return ""


def parse_period_input(user_input: str) -> tuple:
    """사용자가 입력한 기간 문자열을 (시작_YYYY-MM, 종료_YYYY-MM) 튜플로 변환"""
    user_input = user_input.strip()

    # 1) YYYY-MM ~ YYYY-MM (예: 2024-03 ~ 2025-10)
    m = re.match(r"(\d{4})[._\-](\d{1,2})\s*~\s*(\d{4})[._\-](\d{1,2})", user_input)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}", f"{m.group(3)}-{int(m.group(4)):02d}"

    # 2) YYYY ~ YYYY (예: 2024 ~ 2026)
    m = re.match(r"(\d{4})\s*~\s*(\d{4})", user_input)
    if m:
        return f"{m.group(1)}-01", f"{m.group(2)}-12"

    # 3) ~ YYYY 또는 ~ YYYY-MM (예: ~ 2020)
    m = re.match(r"~\s*(\d{4})(?:[._\-](\d{1,2}))?", user_input)
    if m:
        end = f"{m.group(1)}-{int(m.group(2)):02d}" if m.group(2) else f"{m.group(1)}-12"
        return "0000-00", end

    # 4) YYYY ~ 또는 YYYY-MM ~ (예: 2024 ~)
    m = re.match(r"(\d{4})(?:[._\-](\d{1,2}))?\s*~", user_input)
    if m:
        start = f"{m.group(1)}-{int(m.group(2)):02d}" if m.group(2) else f"{m.group(1)}-01"
        return start, "9999-99"

    # 5) 단일 연도 (예: 2025)
    m = re.match(r"^(\d{4})$", user_input)
    if m:
        return f"{m.group(1)}-01", f"{m.group(1)}-12"

    # 6) 단일 연월 (예: 2024-06)
    m = re.match(r"^(\d{4})[._\-](\d{1,2})$", user_input)
    if m:
        d = f"{m.group(1)}-{int(m.group(2)):02d}"
        return d, d

    return "", ""


def get_file_format(file_path: str) -> str:
    return "HWPX" if file_path.lower().endswith(".hwpx") else "HWP"


def main():
    print("=" * 70)
    print(" [통합 문서 기반 기간별 문서 역추적 추출 도구] ")
    print(" 전체 병합 파일에서 특정 기간의 문서만 추출하여 HWPX + TXT를 생성합니다.")
    print("=" * 70)

    # 1. 전체 병합 문서 선택
    txt_path, merged_doc_path = select_merged_document()
    if not txt_path:
        print("\n[오류] 텍스트 파일이 지정되지 않았습니다. 프로그램을 종료합니다.")
        return

    print(f"\n[분석 대상 텍스트 파일]: {os.path.basename(txt_path)}")

    # 2. 텍스트 파일 파싱
    print("문서 목록 및 파일 경로를 분석하는 중입니다...")
    doc_list = parse_merged_txt(txt_path)
    if not doc_list:
        print("\n[오류] 텍스트 파일에서 문서 정보를 추출할 수 없습니다. (헤더 형식이 일치하지 않음)")
        return

    total_docs = len(doc_list)
    valid_dates = [d["date"] for d in doc_list if d["date"]]
    min_date = min(valid_dates) if valid_dates else "알 수 없음"
    max_date = max(valid_dates) if valid_dates else "알 수 없음"

    print(f"  -> 총 {total_docs}개의 문서가 확인되었습니다.")
    print(f"  -> 전체 문서 기간 범위: {min_date} ~ {max_date}")

    # 3. 추출할 기간 입력
    print("\n" + "=" * 60)
    print(" [추출할 기간을 입력하세요]")
    print("   - 예시 1: 2024 ~ 2026       (2024년 1월 ~ 2026년 12월)")
    print("   - 예시 2: 2024-03 ~ 2025-10 (특정 연월 범위)")
    print("   - 예시 3: 2025              (2025년 1년치 전체)")
    print("   - 예시 4: 2024 ~            (2024년 이후 최신 기출 전체)")
    print("=" * 60)

    while True:
        period_input = input("기간 입력: ").strip()
        if not period_input:
            print("기간을 입력해 주세요.")
            continue

        start_date, end_date = parse_period_input(period_input)
        if not start_date:
            print("[오류] 입력 형식을 인식할 수 없습니다. 예시를 참고하여 다시 입력해 주세요.")
            continue
        break

    print(f"\n설정된 검색 범위: {start_date} ~ {end_date}")

    # 4. 대상 문서 필터링
    matched_docs = [
        d for d in doc_list
        if d["date"] and (start_date <= d["date"] <= end_date)
    ]

    if not matched_docs:
        print(f"\n[안내] 입력하신 기간({start_date} ~ {end_date})에 해당하는 문서가 없습니다.")
        return

    total_matched = len(matched_docs)
    print(f"\n[추출 대상 문서: 총 {total_matched}개]")
    for idx, doc in enumerate(matched_docs, 1):
        print(f"  {idx:02d}. [{doc['date']}] {doc['filename']}")

    # 5. 저장 경로 지정
    base_dir = os.path.dirname(txt_path)
    base_name = os.path.splitext(os.path.basename(txt_path))[0]
    period_tag = period_input.replace(" ", "").replace("~", "-")
    suggested_filename = f"{base_name}_{period_tag}.hwpx"

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    try:
        save_path = filedialog.asksaveasfilename(
            parent=root,
            initialdir=base_dir,
            initialfile=suggested_filename,
            title="추출된 파일 저장 위치 지정",
            defaultextension=".hwpx",
            filetypes=[
                ("HWPX 파일", "*.hwpx"),
                ("HWP 파일", "*.hwp")
            ]
        )
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    if not save_path:
        print("\n저장을 취소했습니다. 프로그램을 종료합니다.")
        return

    save_path = os.path.abspath(save_path)
    if save_path.lower().endswith(".hwpx.hwpx"):
        save_path = save_path[:-5]
    elif save_path.lower().endswith(".hwp.hwp"):
        save_path = save_path[:-4]

    txt_save_path = os.path.splitext(save_path)[0] + ".txt"

    # 6. [단계 1/2] 초고속 텍스트 추출 및 새 TXT 저장 (0.01초 소요)
    print("\n[단계 1/2] 지정된 기간의 검색용 TXT 파일 생성 중...")
    header_summary = (
        f"{'=' * 80}\n"
        f"[한글 문서 기간별 추출 텍스트 본문]\n"
        f"- 원본 통합 문서: {os.path.basename(txt_path)}\n"
        f"- 추출 기간: {start_date} ~ {end_date} ({period_input})\n"
        f"- 생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- 추출 문서 수: 총 {total_matched}개\n"
        f"{'=' * 80}\n\n"
    )

    with open(txt_save_path, "w", encoding="utf-8-sig", errors="ignore") as f_out:
        f_out.write(header_summary)
        for doc in matched_docs:
            f_out.write(doc["block_text"])
            f_out.write("\n\n")

    print(f"  -> [완료] TXT 파일 저장 완료: {txt_save_path}")

    # 7. [단계 2/2] 원본 경로 역추적 서식 보존 HWP/HWPX 병합
    print("\n[단계 2/2] 원본 경로 역추적 서식 보존 HWP/HWPX 병합 진행 중...")

    # 원본 파일 존재 여부 검사
    missing_files = [doc for doc in matched_docs if not os.path.exists(doc["filepath"])]
    valid_files = [doc for doc in matched_docs if os.path.exists(doc["filepath"])]

    if missing_files:
        print(f"  [경고] 원본 파일 중 {len(missing_files)}개의 위치를 찾을 수 없습니다.")
        for m in missing_files:
            print(f"    - 누락: {m['filename']} ({m['filepath']})")

    if not valid_files:
        print("\n[오류] 병합할 수 있는 원본 파일이 경로상에 존재하지 않습니다.")
        print("  -> TXT 파일은 정상 생성되었으나, HWP/HWPX 파일은 생성할 수 없습니다.")
        return

    print(f"  -> 유효한 원본 파일 {len(valid_files)}개로 서식 보존 병합을 진행합니다.")

    # 한글 인스턴스 초기화 (화면 렌더링 끄기 초고속 백그라운드 모드)
    print("\n한글 인스턴스를 백그라운드(화면 렌더링 끄기)로 실행하는 중입니다...")
    hwpx = Hwp(new=True, visible=False)
    hwp = hwpx.hwp
    hwp.SetMessageBoxMode(0x00020000)

    try:
        total_valid = len(valid_files)
        for idx, doc in enumerate(valid_files, 1):
            file_path = doc["filepath"]
            filename = doc["filename"]
            fmt = get_file_format(file_path)

            if idx == 1:
                print(f"  ({idx:02d}/{total_valid:02d}) 기준 문서 오픈: {filename}")
                hwp.Open(file_path, fmt, "forceopen:true")
                hwp.MovePos(3, 0, 0)
            else:
                print(f"  ({idx:02d}/{total_valid:02d}) 문서 끼워넣기: {filename}")
                hwp.HAction.GetDefault("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                option = hwp.HParameterSet.HInsertFile
                option.filename = file_path
                option.KeepSection = 1
                option.KeepCharshape = 1
                option.KeepParashape = 1
                option.KeepStyle = 1
                hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                hwp.MovePos(3, 0, 0)

        # 저장
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
        print("기간별 문서 추출 및 병합 작업이 성공적으로 완료되었습니다!")
        print(f"1. 서식 보존 병합 파일: {save_path}")
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
