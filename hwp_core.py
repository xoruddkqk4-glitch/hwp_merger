import os
import re
from datetime import datetime
import pythoncom
from pyhwpx import Hwp


def get_file_format(file_path: str) -> str:
    """파일 확장자에 따라 HWP / HWPX 포맷 문자열 반환"""
    return "HWPX" if file_path.lower().endswith(".hwpx") else "HWP"


def sanitize_text(text: str) -> str:
    """UTF-8 인코딩 불가능한 surrogate 문자 및 null 문자 정제"""
    if not text:
        return ""
    cleaned = text.encode("utf-8", errors="ignore").decode("utf-8")
    return cleaned.replace("\x00", "").strip()


# ==============================================================================
# 1. 파일명 일괄 변경 로직
# ==============================================================================

def remove_copy_suffixes(filename: str) -> str:
    """윈도우 복사본 접미사('의 사본', '- 복사본', ' - Copy' 등) 완벽 제거"""
    name = re.sub(r"[\s._\-]*의\s*사본", "", filename)
    name = re.sub(r"[\s._\-]*복사본(?:\s*\(\d+\))?", "", name)
    name = re.sub(r"[\s._\-]*Copy(?:\s*\(\d+\))?", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+\.", ".", name).strip()
    return name


def standardize_mock_exam_date(name: str) -> str:
    """
    모의고사 및 시험지 파일명의 다양한 날짜 형식을 [YYYY-MM] 표준으로 자동 변환
    예: 2026년 9월 -> [2026-09]
        2025.06 -> [2025-06]
        2024-3 -> [2024-03]
    """
    def repl_hangul(match):
        year, month = match.group(1), int(match.group(2))
        return f"[{year}-{month:02d}]"

    name = re.sub(r"(\d{4})년\s*(\d{1,2})월", repl_hangul, name)

    def repl_dot_dash(match):
        year, month = match.group(1), int(match.group(2))
        return f"[{year}-{month:02d}]"

    name = re.sub(r"(?<!\[)(?<!\d)(20\d{2})[._\-](\d{1,2})(?!\d)", repl_dot_dash, name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def generate_rename_plan(file_paths: list, mode: str, **kwargs) -> list:
    """
    파일명 변경 계획 생성
    반환: list of dict [{"old_path": str, "old_name": str, "new_name": str, "new_path": str, "changed": bool}]
    """
    plan = []
    total_files = len(file_paths)

    for idx, path in enumerate(file_paths, 1):
        dirname, filename = os.path.split(path)
        name_no_ext, ext = os.path.splitext(filename)
        new_name = filename

        if mode == "remove_copy":
            new_name = remove_copy_suffixes(filename)

        elif mode == "replace":
            old_str = kwargs.get("old_str", "")
            new_str = kwargs.get("new_str", "")
            if old_str:
                new_name = filename.replace(old_str, new_str)

        elif mode == "affix":
            prefix = kwargs.get("prefix", "")
            suffix = kwargs.get("suffix", "")
            new_name = f"{prefix}{name_no_ext}{suffix}{ext}"

        elif mode == "mock_date":
            converted_base = standardize_mock_exam_date(name_no_ext)
            new_name = f"{converted_base}{ext}"

        elif mode == "regex":
            pattern = kwargs.get("pattern", "")
            repl = kwargs.get("repl", "")
            if pattern:
                try:
                    new_name = re.sub(pattern, repl, filename)
                except Exception:
                    new_name = filename

        elif mode == "numbering":
            sep = kwargs.get("sep", "_ ")
            start_num = kwargs.get("start_num", 1)
            digits = kwargs.get("digits", max(2, len(str(total_files))))
            curr_num = start_num + idx - 1
            new_name = f"{curr_num:0{digits}d}{sep}{filename}"

        new_path = os.path.join(dirname, new_name)
        plan.append({
            "old_path": path,
            "old_name": filename,
            "new_name": new_name,
            "new_path": new_path,
            "changed": (filename != new_name)
        })

    return plan


def execute_rename(plan: list, log_fn=None) -> tuple:
    """파일명 변경 계획 실행 (성공 수, 실패 수)"""
    success_count = 0
    error_count = 0

    for item in plan:
        if not item["changed"]:
            continue

        old_path = item["old_path"]
        new_path = item["new_path"]
        new_name = item["new_name"]

        try:
            if os.path.exists(new_path) and os.path.abspath(old_path).lower() != os.path.abspath(new_path).lower():
                if log_fn:
                    log_fn(f"[스킵/중복] 이미 존재하는 파일명: {new_name}")
                error_count += 1
                continue

            os.rename(old_path, new_path)
            success_count += 1
            if log_fn:
                log_fn(f"[성공] {item['old_name']} -> {new_name}")
        except Exception as e:
            if log_fn:
                log_fn(f"[실패] {item['old_name']} -> {e}")
            error_count += 1

    return success_count, error_count


# ==============================================================================
# 2. HWP/HWPX 문서 일괄 병합 (merge_hwp)
# ==============================================================================

def merge_hwp_documents(file_list: list, save_path: str, log_fn=None, progress_fn=None, cancel_check=None):
    """
    HWP/HWPX 파일 목록을 하나의 문서로 병합하고 검색용 TXT 파일 동시 생성
    """
    pythoncom.CoInitialize()
    try:
        total_files = len(file_list)
        if total_files == 0:
            raise ValueError("병합할 파일이 없습니다.")

        save_path = os.path.abspath(save_path)
        if save_path.lower().endswith(".hwpx.hwpx"):
            save_path = save_path[:-5]
        elif save_path.lower().endswith(".hwp.hwp"):
            save_path = save_path[:-4]

        txt_save_path = os.path.splitext(save_path)[0] + ".txt"

        if log_fn:
            log_fn(f"병합 대상: 총 {total_files}개 파일")
            log_fn(f"저장 경로: {save_path}")
            log_fn("한글 백그라운드 인스턴스를 초기화하는 중...")

        hwpx = Hwp(new=True, visible=False)
        hwp = hwpx.hwp
        hwp.SetMessageBoxMode(0x00020000)

        try:
            # 1단계: 검색용 TXT 추출 및 생성
            if log_fn:
                log_fn("[단계 1/2] 검색용 TXT 파일 생성 및 텍스트 추출 중...")

            header_summary = (
                f"{'=' * 80}\n"
                f"[한글 문서 병합 텍스트 추출본]\n"
                f"- 생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"- 병합 파일 수: {total_files}개\n"
                f"{'=' * 80}\n\n"
            )

            with open(txt_save_path, "w", encoding="utf-8-sig", errors="ignore") as f_txt:
                f_txt.write(header_summary)

                for idx, file_path in enumerate(file_list, 1):
                    if cancel_check and cancel_check():
                        raise InterruptedError("사용자에 의해 작업이 취소되었습니다.")

                    filename = os.path.basename(file_path)
                    if log_fn:
                        log_fn(f"  ({idx:03d}/{total_files:03d}) 텍스트 추출 중: {filename}")
                    if progress_fn:
                        progress_fn(idx, total_files * 2, f"텍스트 추출 ({idx}/{total_files})")

                    fmt = get_file_format(file_path)
                    hwp.Open(file_path, fmt, "forceopen:true")
                    raw_content = hwpx.get_text_file("UNICODE", option="") or ""
                    content = sanitize_text(raw_content)

                    section_header = (
                        f"{'=' * 80}\n"
                        f"[{idx:03d}/{total_files:03d}] {filename}\n"
                        f"- 원본 경로: {file_path}\n"
                        f"{'=' * 80}\n\n"
                    )
                    f_txt.write(section_header)
                    f_txt.write(content)
                    f_txt.write("\n\n")
                    f_txt.flush()
                    hwp.Clear(1)

            if log_fn:
                log_fn(f"-> TXT 파일 저장 완료: {txt_save_path}")

            # 2단계: 서식 보존 HWP/HWPX 문서 병합
            if log_fn:
                log_fn("[단계 2/2] 원본 서식 보존 문서 결합 진행 중...")

            for idx, file_path in enumerate(file_list, 1):
                if cancel_check and cancel_check():
                    raise InterruptedError("사용자에 의해 작업이 취소되었습니다.")

                filename = os.path.basename(file_path)
                fmt = get_file_format(file_path)

                if idx == 1:
                    if log_fn:
                        log_fn(f"  ({idx:03d}/{total_files:03d}) 기준 문서 오픈: {filename}")
                    hwp.Open(file_path, fmt, "forceopen:true")
                    hwp.MovePos(3, 0, 0)
                else:
                    if log_fn:
                        log_fn(f"  ({idx:03d}/{total_files:03d}) 문서 끼워넣기: {filename}")
                    hwp.HAction.GetDefault("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                    option = hwp.HParameterSet.HInsertFile
                    option.filename = file_path
                    option.KeepSection = 1
                    option.KeepCharshape = 1
                    option.KeepParashape = 1
                    option.KeepStyle = 1
                    hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                    hwp.MovePos(3, 0, 0)

                if progress_fn:
                    progress_fn(total_files + idx, total_files * 2, f"서식 병합 ({idx}/{total_files})")

            # 최종 파일 저장
            save_format = get_file_format(save_path)
            if log_fn:
                log_fn(f"병합 문서를 {save_format} 포맷으로 저장 중입니다: {save_path}")

            hwp.HAction.GetDefault("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)
            save_option = hwp.HParameterSet.HFileOpenSave
            save_option.Attributes = 0
            save_option.filename = save_path
            save_option.Format = save_format
            hwp.HAction.Execute("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)

            if log_fn:
                log_fn(f"-> [완료] 병합 문서 저장 완료: {save_path}")
                log_fn(f"-> [완료] 검색 TXT 저장 완료: {txt_save_path}")

        finally:
            try:
                hwp.Quit()
            except Exception:
                pass

    finally:
        pythoncom.CoUninitialize()


# ==============================================================================
# 3. 최신순 맨 앞 증분 병합 (prepend_hwp)
# ==============================================================================

def prepend_hwp_documents(base_file: str, new_files: list, save_path: str, log_fn=None, progress_fn=None, cancel_check=None):
    """
    기존 대용량 병합본 앞에 신규 파일(들)을 최신순으로 초고속 맨 앞 결합
    """
    pythoncom.CoInitialize()
    try:
        total_new = len(new_files)
        if total_new == 0:
            raise ValueError("추가할 신규 파일이 없습니다.")
        if not os.path.exists(base_file):
            raise FileNotFoundError(f"기존 병합 파일을 찾을 수 없습니다: {base_file}")

        save_path = os.path.abspath(save_path)
        if save_path.lower().endswith(".hwpx.hwpx"):
            save_path = save_path[:-5]
        elif save_path.lower().endswith(".hwp.hwp"):
            save_path = save_path[:-4]

        txt_save_path = os.path.splitext(save_path)[0] + ".txt"
        base_txt_path = os.path.splitext(base_file)[0] + ".txt"

        if log_fn:
            log_fn(f"기존 파일: {os.path.basename(base_file)}")
            log_fn(f"추가할 신규 파일: 총 {total_new}개")
            log_fn("한글 백그라운드 인스턴스를 초기화하는 중...")

        hwpx = Hwp(new=True, visible=False)
        hwp = hwpx.hwp
        hwp.SetMessageBoxMode(0x00020000)

        try:
            # 1단계: 검색용 TXT 증분 병합
            if log_fn:
                log_fn("[단계 1/2] 신규 파일 텍스트 추출 및 증분 TXT 결합 중...")

            new_txt_sections = []
            header_summary = (
                f"{'=' * 80}\n"
                f"[한글 문서 증분 병합 텍스트 (최신 파일 맨 앞 추가)]\n"
                f"- 추가 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"- 신규 추가 파일 수: {total_new}개\n"
                f"{'=' * 80}\n\n"
            )
            new_txt_sections.append(header_summary)

            for idx, file_path in enumerate(new_files, 1):
                if cancel_check and cancel_check():
                    raise InterruptedError("사용자에 의해 작업이 취소되었습니다.")

                filename = os.path.basename(file_path)
                if log_fn:
                    log_fn(f"  - 신규 파일 텍스트 추출 ({idx}/{total_new}): {filename}")
                if progress_fn:
                    progress_fn(idx, total_new * 2 + 1, f"신규 텍스트 추출 ({idx}/{total_new})")

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

            existing_txt = ""
            if os.path.exists(base_txt_path):
                try:
                    with open(base_txt_path, "r", encoding="utf-8-sig", errors="ignore") as f_old:
                        existing_txt = f_old.read()
                    if log_fn:
                        log_fn(f"  - 기존 TXT 파일({os.path.basename(base_txt_path)}) 내용 결합")
                except Exception as read_err:
                    if log_fn:
                        log_fn(f"  [주의] 기존 TXT 파일 읽기 실패: {read_err}")

            with open(txt_save_path, "w", encoding="utf-8-sig", errors="ignore") as f_txt:
                f_txt.writelines(new_txt_sections)
                if existing_txt:
                    f_txt.write(f"\n\n{'#' * 80}\n# [기존 통합 문서 내용 이어짐]\n{'#' * 80}\n\n")
                    f_txt.write(existing_txt)

            if log_fn:
                log_fn(f"-> TXT 파일 저장 완료: {txt_save_path}")

            # 2단계: 신규 파일 오픈 -> 나머지 신규 InsertFile -> 기존 대용량 단 1회 InsertFile
            if log_fn:
                log_fn("[단계 2/2] 원본 서식 보존 증분 문서 결합 중...")

            first_new = new_files[0]
            fmt_first = get_file_format(first_new)
            if log_fn:
                log_fn(f"  - 첫 번째 신규 기준 문서 오픈: {os.path.basename(first_new)}")
            hwp.Open(first_new, fmt_first, "forceopen:true")
            hwp.MovePos(3, 0, 0)

            for idx, file_path in enumerate(new_files[1:], 2):
                if cancel_check and cancel_check():
                    raise InterruptedError("사용자에 의해 작업이 취소되었습니다.")

                filename = os.path.basename(file_path)
                if log_fn:
                    log_fn(f"  - 다음 신규 문서 끼워넣기 ({idx}/{total_new}): {filename}")
                hwp.HAction.GetDefault("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                option = hwp.HParameterSet.HInsertFile
                option.filename = file_path
                option.KeepSection = 1
                option.KeepCharshape = 1
                option.KeepParashape = 1
                option.KeepStyle = 1
                hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                hwp.MovePos(3, 0, 0)
                if progress_fn:
                    progress_fn(total_new + idx - 1, total_new * 2 + 1, f"신규 문서 병합 ({idx}/{total_new})")

            # 기존 대용량 파일 1회 결합
            if log_fn:
                log_fn(f"  - 기존 대용량 병합본 단 1회 결합: {os.path.basename(base_file)}")
            hwp.HAction.GetDefault("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
            option = hwp.HParameterSet.HInsertFile
            option.filename = base_file
            option.KeepSection = 1
            option.KeepCharshape = 1
            option.KeepParashape = 1
            option.KeepStyle = 1
            hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
            hwp.MovePos(3, 0, 0)

            if progress_fn:
                progress_fn(total_new * 2 + 1, total_new * 2 + 1, "최종 문서 저장 중")

            save_format = get_file_format(save_path)
            hwp.HAction.GetDefault("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)
            save_option = hwp.HParameterSet.HFileOpenSave
            save_option.Attributes = 0
            save_option.filename = save_path
            save_option.Format = save_format
            hwp.HAction.Execute("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)

            if log_fn:
                log_fn(f"-> [완료] 최신순 증분 문서 저장 완료: {save_path}")
                log_fn(f"-> [완료] 최신순 증분 TXT 저장 완료: {txt_save_path}")

        finally:
            try:
                hwp.Quit()
            except Exception:
                pass

    finally:
        pythoncom.CoUninitialize()


# ==============================================================================
# 4. 기간별 문서 역추적 추출 (extract_by_period)
# ==============================================================================

def extract_date_from_name(filename: str) -> str:
    """파일명에서 YYYY-MM 형식의 날짜 추출"""
    m = re.search(r"\[(\d{4})[-._](\d{1,2})", filename)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    m = re.search(r"(?<!\d)(20\d{2}|19\d{2})[-._](\d{1,2})", filename)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    m = re.search(r"(\d{4})년\s*(\d{1,2})월", filename)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    m = re.search(r"\b(20\d{2}|19\d{2})\b", filename)
    if m:
        return f"{m.group(1)}-01"

    return ""


def parse_period_input(user_input: str) -> tuple:
    """기간 문자열을 (시작_YYYY-MM, 종료_YYYY-MM) 튜플로 변환"""
    user_input = user_input.strip()
    m = re.match(r"(\d{4})[._\-](\d{1,2})\s*~\s*(\d{4})[._\-](\d{1,2})", user_input)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}", f"{m.group(3)}-{int(m.group(4)):02d}"

    m = re.match(r"(\d{4})\s*~\s*(\d{4})", user_input)
    if m:
        return f"{m.group(1)}-01", f"{m.group(2)}-12"

    m = re.match(r"~\s*(\d{4})(?:[._\-](\d{1,2}))?", user_input)
    if m:
        end = f"{m.group(1)}-{int(m.group(2)):02d}" if m.group(2) else f"{m.group(1)}-12"
        return "0000-00", end

    m = re.match(r"(\d{4})(?:[._\-](\d{1,2}))?\s*~", user_input)
    if m:
        start = f"{m.group(1)}-{int(m.group(2)):02d}" if m.group(2) else f"{m.group(1)}-01"
        return start, "9999-99"

    m = re.match(r"^(\d{4})$", user_input)
    if m:
        return f"{m.group(1)}-01", f"{m.group(1)}-12"

    m = re.match(r"^(\d{4})[._\-](\d{1,2})$", user_input)
    if m:
        d = f"{m.group(1)}-{int(m.group(2)):02d}"
        return d, d

    return "", ""


def parse_merged_txt(txt_path: str) -> list:
    """병합된 TXT 파일에서 각 문서 정보 및 텍스트 블록 파싱"""
    with open(txt_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        content = f.read()

    pattern = r"={40,}\s*\n\[\s*(\d+)/(\d+)\s*\]\s*([^\n]+)\n-\s*원본 경로:\s*([^\n]+)\n={40,}"
    matches = list(re.finditer(pattern, content))

    if not matches:
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

        start_pos = m.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        block_text = content[start_pos:end_pos].strip()

        doc_date = extract_date_from_name(filename)

        parsed_docs.append({
            "index": int(curr_idx) if curr_idx.isdigit() else idx + 1,
            "filename": filename,
            "filepath": filepath,
            "date": doc_date,
            "block_text": block_text
        })

    return parsed_docs


def extract_period_documents(txt_path: str, matched_docs: list, period_input: str, start_date: str, end_date: str, save_path: str, log_fn=None, progress_fn=None, cancel_check=None):
    """
    필터링된 문서들을 대상으로 TXT 파일 생성 및 원본 서식 역추적 결합 수행
    """
    pythoncom.CoInitialize()
    try:
        total_matched = len(matched_docs)
        if total_matched == 0:
            raise ValueError("추출할 문서가 없습니다.")

        save_path = os.path.abspath(save_path)
        if save_path.lower().endswith(".hwpx.hwpx"):
            save_path = save_path[:-5]
        elif save_path.lower().endswith(".hwp.hwp"):
            save_path = save_path[:-4]

        txt_save_path = os.path.splitext(save_path)[0] + ".txt"

        # 1단계: TXT 파일 생성
        if log_fn:
            log_fn("[단계 1/2] 지정 기간 검색용 TXT 파일 생성 중...")

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

        if log_fn:
            log_fn(f"-> TXT 저장 완료: {txt_save_path}")

        # 2단계: 원본 파일 존재 검사 및 서식 보존 병합
        missing_files = [doc for doc in matched_docs if not os.path.exists(doc["filepath"])]
        valid_files = [doc for doc in matched_docs if os.path.exists(doc["filepath"])]

        if missing_files and log_fn:
            log_fn(f"[경고] 원본 파일 {len(missing_files)}개의 위치를 찾을 수 없습니다.")

        if not valid_files:
            raise FileNotFoundError("병합할 수 있는 원본 파일이 경로상에 존재하지 않습니다.")

        total_valid = len(valid_files)
        if log_fn:
            log_fn(f"[단계 2/2] 원본 경로 역추적 서식 보존 문서 병합 중 (유효 파일: {total_valid}개)...")

        hwpx = Hwp(new=True, visible=False)
        hwp = hwpx.hwp
        hwp.SetMessageBoxMode(0x00020000)

        try:
            for idx, doc in enumerate(valid_files, 1):
                if cancel_check and cancel_check():
                    raise InterruptedError("사용자에 의해 작업이 취소되었습니다.")

                file_path = doc["filepath"]
                filename = doc["filename"]
                fmt = get_file_format(file_path)

                if idx == 1:
                    if log_fn:
                        log_fn(f"  ({idx:02d}/{total_valid:02d}) 기준 문서 오픈: {filename}")
                    hwp.Open(file_path, fmt, "forceopen:true")
                    hwp.MovePos(3, 0, 0)
                else:
                    if log_fn:
                        log_fn(f"  ({idx:02d}/{total_valid:02d}) 문서 끼워넣기: {filename}")
                    hwp.HAction.GetDefault("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                    option = hwp.HParameterSet.HInsertFile
                    option.filename = file_path
                    option.KeepSection = 1
                    option.KeepCharshape = 1
                    option.KeepParashape = 1
                    option.KeepStyle = 1
                    hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
                    hwp.MovePos(3, 0, 0)

                if progress_fn:
                    progress_fn(idx, total_valid, f"문서 결합 중 ({idx}/{total_valid})")

            save_format = get_file_format(save_path)
            hwp.HAction.GetDefault("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)
            save_option = hwp.HParameterSet.HFileOpenSave
            save_option.Attributes = 0
            save_option.filename = save_path
            save_option.Format = save_format
            hwp.HAction.Execute("FileSaveAs_S", hwp.HParameterSet.HFileOpenSave.HSet)

            if log_fn:
                log_fn(f"-> [완료] 추출 문서 저장 완료: {save_path}")
                log_fn(f"-> [완료] 추출 TXT 저장 완료: {txt_save_path}")

        finally:
            try:
                hwp.Quit()
            except Exception:
                pass

    finally:
        pythoncom.CoUninitialize()
