# Agent Execution Rules: HWP Merger (한글 문서 병합 도구)

에이전트 실행 규칙: 터미널 전용 고속 검증 (`.agents/rules/rules.md`)

## 1. Browser & Scratchpad Policy (브라우저 및 시각 검증 정책)
- **엄격 금지:** 일반적인 코드 수정 작업 중 브라우저(Chrome, Scratchpad 등)를 구동하거나 시각 검증을 자동으로 수행하지 않습니다.
- **자동 스크린샷 금지:** 코드 수정 후 스크린샷 촬영이나 브라우저 시각 검사를 일체 자동으로 수행하지 않습니다.
- 이 프로젝트는 한글 문서(HWP/HWPX) 병합 파이썬 스크립트 도구입니다. 웹 브라우저 구동 및 시각 검증이 불필요합니다.
- **명시적 예외 조건:** 오직 사용자가 `/scratchpad`, `/action scratchpad` 명령어를 명시적으로 입력하거나 "scratchpad로 검증해줘"라고 직접 요청한 경우에 한해 본 정책의 예외가 적용되어 Scratchpad / 브라우저 시각 검증 도구를 구동할 수 있습니다.

## 2. Terminal-Based Error Verification (터미널 기반 정적 오류 검증)
- 코드 변경 후에는 브라우저 확인 대신 터미널 명령으로 빠른 정적 검증만 수행합니다.
- **이 프로젝트(파이썬) 기본 검증 명령:**
  ```bash
  python -m py_compile <수정한_파일.py>
  ```
- `py_compile`은 구문 오류만 잡고 `NameError`/`AttributeError` 같은 런타임 오류는 잡지 못하므로, 필요시 최소 실행 스니펫이나 단위 로직으로 확인합니다.
- 경미한 경고는 끝없이 고치려 하지 말고 간단히 보고 후 종료합니다.
- 무거운 데브 서버나 빌드 명령어를 임의로 실행하지 않습니다.

## 3. Workflow Optimization (일반 수정 모드)
- **일반적 코드 수정/오류 복구 작업 시:**
  - 코드 변경을 적용하고 빠른 터미널 오류 검증(구문/정합성 검사)만 수행한 후 즉시 작업을 종료합니다.
  - **절대로 자동으로 Git 커밋(`git commit`) 및 푸시(`git push`)를 수행하지 않습니다.**
- 사용자가 명시적으로 `/git-commit` 명령어를 입력할 때까지 커밋/푸시 없이 대기합니다.

## 4. Git 커밋 및 푸시 정책 (오직 `/git-commit` 명령어 수신 시에만 실행)
- **엄격 조건:** 오직 사용자로부터 `/action git-commit`, `/git-commit`, 또는 "README 업데이트 후 푸시"와 같은 **명시적인 커밋/푸시 명령어**를 수신했을 때만 Git 커밋 및 푸시 워크플로우를 수행합니다.
- **일반 수정 시 자동 커밋 금지:** 기능 구현, 버그 수정, 코드 리팩토링 등 일반적인 요청 시에는 코드 수정과 터미널 오류 검증만 진행하고 커밋/푸시는 절대로 자동으로 실행하지 않습니다.
- **`/git-commit` 수신 시 수행 절차:**
  1. 작업 내용 및 검증 결과를 정리하여 `README.md` 하단에 누적 이력을 작성합니다.
  2. 상세한 커밋 메시지와 함께 `git add .` 및 `git commit`을 진행합니다.
  3. GitHub 원격 저장소(`main` 브랜치)로 `git push`를 수행하고 결과를 사용자에게 종합 보고합니다.
- `README.md` 업데이트 시 코드 수정 사항, 새로 구현된 기능, 발생한 문제 및 해결 과정, 검증 결과를 명확하게 기록해야 합니다.
- **`README.md` 변경 이력 누적 기록 규칙:**
  - `README.md` 파일을 수정할 때, 업데이트되는 내용을 `README.md` 파일의 맨 뒷부분(하단)에 **날짜 및 시간(서울 기준 시각: YYYY-MM-DD HH:mm)** 기준으로 누적하여 기록해야 합니다.
  - 누적 기록에는 **날짜 및 시간(Date & Time, 서울 기준 KST)**, **커밋 ID(Commit Hash)**, **수정 내용(Modification Details)**이 반드시 포함되어야 합니다.
  - `README.md`의 기존 본문 내용을 수정하는 것도 허용되며, 변경 이력은 맨 뒷부분에 지속해서 누적됩니다.
- 커밋 메시지는 한국어로 작성하며, `docs: update README.md and detailed commit results` 포맷을 따릅니다.

## 5. `/ask` 질의응답 및 계획 전용 모드 정책 (No Code Modification & No Auto-Execution)
- 사용자로부터 `/ask`, `/action ask`, 또는 `/ask`로 시작하는 질의를 받으면 프로젝트 소스 코드를 절대로 수정하지 않아야 합니다.
- 단순 질문인 경우 대화 답변만 수행하고, 기술적/복잡한 변경 요청인 경우 `implementation_plan.md` 계획서 작성까지만 진행합니다.
- **계획서 자동 실행 금지:** `/ask` 모드로 작성된 계획서는 시스템 자동 승인(Auto-Approve/Proceed)이 전달되더라도 절대로 자동으로 코드를 변경해서는 안 되며, 사용자의 명시적인 추가 대화 명령이 있을 때까지 대기해야 합니다.

## 6. `/scratchpad` 브라우저 검증 전용 모드 정책 (Visual Verification Explicit Exception)
- 사용자로부터 `/scratchpad`, `/action scratchpad`, 또는 "scratchpad로 검증해줘"라는 명시적인 요청을 수신하는 경우, Rule 1 정책의 명시적 예외를 적용합니다.
- Scratchpad 및 브라우저 검증 도구(`browser_subagent`)를 활용하여 대상 페이지 및 UI 인터액션 기능을 시각적으로 직접 확인하고 결과를 사용자에게 보고합니다.
