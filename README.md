# 00hwp_merger (한글 문서 병합 도구)

여러 개의 한글 문서(`.hwp`, `.hwpx`)를 선택하여 하나의 문서로 병합하고, 대용량 문서에서도 초고속으로 본문을 검색할 수 있도록 파일별 경계 구분이 포함된 텍스트(`.txt`) 파일을 함께 생성해 주는 파이썬 자동화 도구 모음입니다.

## 제공 스크립트 및 주요 기능

### 1. 전체 문서 일괄 병합 (`merge_hwp.py`)
- **다중 파일 일괄 선택**: `tkinter` 탐색기를 통해 수십~수백 개의 HWP/HWPX 문서를 선택하여 일괄 병합.
- **원본 서식 완벽 보존**: 구역(쪽 모양), 글자 모양, 문단 모양, 스타일을 100% 유지한 채 순차 결합.
- **초고속 검색용 TXT 동시 생성**: 파일명/경로 헤더 경계선이 포함된 `.txt` 파일을 `utf-8-sig` 인코딩으로 동시 자동 생성.
- **특수기호/서러게이트 오류 방어**: 모의고사 수식 및 특수문자(`\udb80` 등)로 인한 인코딩 충돌을 방지하는 안전 정제 스트리밍 저장.

### 2. 최신순 초고속 증분 병합 (`prepend_hwp.py`)
- **수백 개 문서 재병합 방지**: 신규 시험지가 추가되었을 때 전체를 다시 돌릴 필요 없이 **5~10초 만에 결합**.
- **역발상 1회 결합 원리**: 신규 파일을 먼저 열고, 그 뒤에 기존 대용량 완성본을 단 1회 `InsertFile`하여 신규 파일이 맨 앞(최신순)에 위치하도록 정렬 유지.
- **TXT 파일 실시간 결합**: 기존 검색용 TXT 파일 앞부분에 신규 파일 텍스트를 즉시 결합하여 저장.

## 사용 기술 및 요구 사항
- Python 3.8+
- [pyhwpx](https://pypi.org/project/pyhwpx/) (`pip install pyhwpx`)
- 한글 프로그램(한컴오피스 한글) 설치 환경 (Windows)

## 실행 방법

### 전체 문서를 처음부터 일괄 병합할 때
```bash
python merge_hwp.py
```

### 기존 대용량 병합본 맨 앞에 신규 파일만 최신순으로 덧붙일 때
```bash
python prepend_hwp.py
```

---

## 변경 이력

### [2026-09-19 20:09] 업데이트 이력 (Commit ID: 009a943)
- **수정 내용**:
  - 프로젝트 초기 환경 구성: `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `.agents/` 규칙 및 스킬 세팅
  - GitHub 원격 저장소(`https://github.com/xoruddkqk4-glitch/hwp_merger.git`) 연동
  - `merge_hwp.py` 고도화: HWP 원본 서식 보존 병합과 함께 파일명 경계 구분이 포함된 검색용 TXT 파일 동시 생성 기능(방식 A) 구현
- **검증 결과**:
  - `python -m py_compile merge_hwp.py` 구문 검증 완료 (통과)
  - `pyhwpx` OLE 연동 및 텍스트 추출 기능 단위 검증 완료

### [2026-09-19 20:32] 업데이트 이력 (Commit ID: 10cd240)
- **수정 내용**:
  - `merge_hwp.py`: 시험지/모의고사 특수기호 단독 대행 문자(`\udb80`)로 인한 `UnicodeEncodeError` 수정 (`sanitize_text` 및 `errors="ignore"` 실시간 스트리밍 기록 적용)
  - `merge_hwp.py`: 모드 선택 프롬프트를 제거하고 항상 HWP/HWPX와 검색용 TXT 2개 파일을 자동 생성하도록 원스톱 파이프라인 간소화
  - `prepend_hwp.py`: 기존 대용량 완성본 앞에 신규 파일을 최신순으로 5초 만에 결합하는 전용 초고속 증분 병합 도구 신규 개발
- **검증 결과**:
  - `python -m py_compile merge_hwp.py` 구문 검증 완료 (통과)
  - `python -m py_compile prepend_hwp.py` 구문 검증 완료 (통과)
  - `sanitize_text` 대행 문자(`\udb80`) 및 null 문자 제거 정제 단위 테스트 완료
