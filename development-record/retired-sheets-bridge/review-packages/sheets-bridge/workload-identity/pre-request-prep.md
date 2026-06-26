# Workload Identity Pre-Request Prep

## Goal

SRE/보안팀에 요청하기 전에 사용자가 미리 확정할 수 있는 입력값,
정책 초안, 로컬 검증 결과, 첨부 자료를 준비한다. 요청 시에는
"무엇을 승인해야 하는지"만 남기고, 설계 판단과 테스트 범위는 이
패키지로 설명한다.

## 먼저 확정할 값

| 항목 | 사용자가 미리 정할 값 | 예시 |
| --- | --- | --- |
| GCP project | 배포 대상 project id | `day1-dev` |
| region | Cloud Run region | `asia-northeast3` |
| broker service | Cloud Run service 이름 | `cloud-run-sheets-broker` |
| runtime identity | Cloud Run 실행 identity | `...@...iam.gserviceaccount.com` |
| delegated identity | DWD에 사용할 delegated identity | `...@...iam.gserviceaccount.com` |
| broker audience | broker identity evidence audience | `32555940559.apps.googleusercontent.com` for current gcloud smoke |
| hosted domain | 허용할 Workspace domain | `day1company.co.kr` |
| pilot spreadsheet | smoke test 대상 spreadsheet id | `<spreadsheet-id>` |
| pilot sheet/range | smoke test 대상 sheet id와 A1 range | `0`, `Sheet1!A1:B10` |

## 요청 전 사용자가 할 수 있는 일

1. Pilot 범위를 작게 정한다.
   - 첫 smoke는 `inspect.metadata`와 `inspect.values_window` 정도로 제한한다.
   - 승인 spreadsheet, sheet id, A1 range를 하나만 고른다.

2. Broker policy 초안을 좁게 만든다.
   - 가능한 한 특정 principal, 특정 spreadsheet, 특정 range로 시작한다.
   - 전체 도메인 또는 wildcard 정책은 운영 승인 이후 확장한다.

3. 로컬 테스트를 통과시킨다.
   - broker unit test
   - runtime contract 문서 검토
   - credential-free wording scan

4. SRE/보안팀용 첨부자료를 정리한다.
   - `sre-security-workload-identity-flow.svg`
   - `request.draft.md`
   - `readonly-policy.pilot.draft.json`
   - `pilot-values.draft.env`
   - `sre-smoke-commands.draft.sh`
   - `local-preflight-result.md`
   - 로컬 테스트 결과

## 아직 요청이 필요한 일

| 담당 | 필요한 일 | 사용자가 줄 수 있는 입력 |
| --- | --- | --- |
| SRE | Cloud Run runtime identity 설정 | project, region, service, identity |
| SRE | IAM Credentials API와 Sheets API 활성화 | project id |
| SRE | runtime identity에 IAM Credentials `signJwt` 권한 부여 | runtime identity, delegated identity |
| SRE | 환경변수 설정 및 배포 | env 값, policy JSON |
| SRE | authorized `/v1/inspect` smoke 실행 | pilot spreadsheet/range |
| 보안팀 | DWD 승인 | delegated identity OAuth client id, scope |
| 보안팀 | 허용 사용자/도메인 경계 승인 | principal/domain 정책 |
| 보안팀 | audit log 보존 기준 승인 | audit field 목록 |
| 보안팀 | 외부 소유 spreadsheet 정책 결정 | ACL 기반 허용 여부 |

## 권장 첫 승인 범위

첫 단계는 읽기 전용 pilot로 제한한다.

- operations:
  - `inspect.metadata`
  - `inspect.values_window`
  - `inspect.formula_window`
  - `inspect.grid_window`
- scope:
  - `https://www.googleapis.com/auth/spreadsheets.readonly`
- risk:
  - `low`
- write/apply:
  - 첫 승인에서는 제외

## Done When

- 요청서에 들어갈 값이 모두 채워져 있다.
- pilot policy가 JSON으로 유효하다.
- 로컬 unit test가 통과한다.
- SVG와 요청 템플릿이 첨부 가능하다.
- SRE/보안팀이 실행할 명령과 승인 항목이 분리되어 있다.

## Current Draft Package

- `pilot-values.draft.env`: 현재 repo context로 채운 pilot 값. 단,
  production audience를 별도로 둘지는 SRE/보안팀 확인 필요.
- `readonly-policy.pilot.draft.json`: 특정 사용자, spreadsheet, sheet,
  range로 제한한 read-only policy.
- `request.draft.md`: SRE/보안팀 전달용 요청서 초안.
- `sre-smoke-commands.draft.sh`: SRE 실행용 명령 초안. `BROKER_AUDIENCE`
  확인 전에는 실행을 중단한다.
- `local-preflight-result.md`: 로컬 검증 결과.
- `current-broker-check.md`: 현재 배포 broker의 live check 결과. Identity
  evidence는 통과했고 IAM Credentials `signJwt` 권한에서 막힌 상태.
