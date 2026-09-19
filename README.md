# 00hwp_merger (한글 문서 병합 도구)

여러 개의 한글 문서(`.hwp`, `.hwpx`)를 선택하여 하나의 문서로 병합하는 파이썬 자동화 도구입니다.

## 주요 기능
- **다중 파일 선택 GUI**: `tkinter` 파일 선택창을 통해 손쉽게 병합할 문서들을 선택할 수 있습니다.
- **포맷 유지 HWP 병합**: `pyhwpx` 라이브러리를 활용하여 구역(쪽 모양), 글자 모양, 문단 모양, 스타일을 유지한 채 순차적으로 문서를 결합합니다.
- **초고속 검색용 TXT 동시 병합**: 대용량 HWP의 검색 버벅임을 보완하기 위해 문서별 명확한 경계(파일명, 원본 경로 헤더)가 포함된 경량 텍스트 파일(`.txt`)을 함께 자동 생성합니다 (`utf-8-sig` 인코딩).
- **저장 위치 및 포맷 자동 분기**: 병합된 문서를 원하는 경로와 파일명(`.hwp` 또는 `.hwpx`)으로 지정하여 저장합니다.

## 사용 기술 및 요구 사항
- Python 3.8+
- [pyhwpx](https://pypi.org/project/pyhwpx/) (`pip install pyhwpx`)
- 한글 프로그램(한컴오피스 한글) 설치 환경 (Windows)

## 실행 방법
```bash
python merge_hwp.py
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
