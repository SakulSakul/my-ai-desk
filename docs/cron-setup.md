# alarm-dispatch 재가동 — 외부 크론 배선 안내 (사람 작업)

> **왜 필요한가**
> `alarm-dispatch` 워크플로는 2026-07-02 이후 한 번도 실행되지 않았다. 워크플로가
> 고장난 게 아니라 **쏴줄 외부 트리거가 아직 없다** — `repository_dispatch` 이벤트가
> 07-01이 마지막이다. 현재 알림은 `daily_alarm`의 `schedule:`(fallback)이 내보내고
> 있는데, GitHub Actions의 **schedule은 60일간 저장소 활동이 없으면 자동 비활성화**된다.
> 옵션 B(스케줄 외재화)는 바로 이 시한폭탄을 없애려는 설계이고, 외부 크론 배선이
> 그 마지막 한 조각이다.
>
> **소요 시간 약 5분.** 아래 값은 그대로 복사해 쓰면 된다.
> `<...>` 자리표시자만 본인 값으로 채운다 — **이 문서에 실제 토큰을 적지 말 것.**

---

## 0. 먼저: 지금 당장 경로가 살아있는지 확인 (선택, 30초)

배선 전에 3주 잠든 경로가 정상인지 눈으로 확인하고 싶다면:

**Actions → alarm-dispatch → Run workflow → branch `main` → 실행**

전 스텝(Supabase ping → dead-man A → telegram → kakao → dead-man B)이 초록이면
"경로 정상, 트리거만 부재"가 확정된다. 이날 알림이 한 번 더 오는 것은 정상이다.

> 참고: 이 확인은 Claude Code가 대신 못 한다. 세션 토큰에 Actions 실행 권한이 없어
> `repository_dispatch`·`workflow_dispatch` 모두 403으로 거부된다(실측).

---

## 1. GitHub PAT 발급

**Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**

| 항목 | 값 |
|---|---|
| Token name | `my-ai-desk-daily-alarm` |
| Expiration | **1년** |
| Repository access | **Only select repositories** → `SakulSakul/my-ai-desk` 하나만 |
| Permissions | **Contents: Read and write** (이것 하나면 `dispatches` 발사 가능) |

발급된 `github_pat_...` 값을 복사해 둔다(다시 볼 수 없다).

> ⚠️ **만료일을 폰 캘린더에 지금 등록하세요.** 1년 뒤 토큰이 만료되면 알림이
> 조용히 멈춘다 — 그때 원인을 찾느라 헤매지 않으려면 만료 1주 전 알림을 걸어둘 것.
> (아래 4번 healthchecks를 걸어두면 이 사고도 이메일로 잡힌다.)

---

## 2. cron-job.org 잡 생성

[cron-job.org](https://cron-job.org) 가입 후 **Create cronjob**:

| 항목 | 값 |
|---|---|
| Title | `my-ai-desk daily alarm` |
| URL | `https://api.github.com/repos/SakulSakul/my-ai-desk/dispatches` |
| Method | **POST** |
| Schedule | 매일 **06:00 (Asia/Seoul)** — 사이트가 UTC만 받으면 **21:00 UTC** |
| Request body | `{"event_type":"daily-alarm"}` |
| 실패 알림 | **이메일 ON** |

**헤더 3종** (Advanced → Headers):

```
Authorization: Bearer <1번에서 발급한 PAT>
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

**정상 응답은 `204 No Content`** (본문 없음). 401/403이면 PAT 권한·만료를,
404면 URL 오타나 저장소 접근 범위를 확인한다.

### 왜 06:00인가

`daily_alarm`은 설정상 06:30이지만 GitHub의 schedule 지연으로 **실제로는 07:2x경**
발송된다(14일 연속 관측). 06:00으로 잡으면 병행 기간에 **먼저 온 알림 = alarm-dispatch,
나중 것 = daily_alarm**으로 육안 식별이 된다. 어느 경로가 살아있는지 헷갈리지 않는다.

---

## 3. healthchecks.io — 조용한 실패 감지

[healthchecks.io](https://healthchecks.io) 가입 후 **체크 2개** 생성.
둘 다 **Period: 1 day / Grace: 2 hours**:

| 체크 이름 | 용도 | 등록할 GitHub Secret |
|---|---|---|
| `my-ai-desk cron alive` | 크론이 도달했는지 | `HEALTHCHECK_CRON_URL` |
| `my-ai-desk alarm sent` | 알림이 실제로 나갔는지 | `HEALTHCHECK_SENT_URL` |

각 체크의 **Ping URL**을 복사해 **Settings → Secrets and variables → Actions →
New repository secret** 에 위 이름으로 등록한다.

두 개로 나눈 이유: 크론은 도달했는데 알림만 실패하는 경우를 구분하기 위해서다.
`cron alive`는 Supabase 핑 직후, `alarm sent`는 모든 알림 스텝 성공 후에만 울린다.

> 등록 전까지 워크플로의 dead-man 스텝은 "미설정 — 감시 비활성" 로그를 남기고
> **skip된다. 이는 오류가 아니라 정상 동작이다.**

---

## 4. 배선 후 7일 관측

배선이 끝나면 **알림이 하루 두 세트 오는 것이 정상**이다(alarm-dispatch 06:00 +
daily_alarm 07:2x). 이 병행 기간에 확인할 것:

- [ ] 매일 alarm-dispatch가 성공하는가 (Actions 탭)
- [ ] cron-job.org 실행 이력이 매일 204인가
- [ ] healthchecks 두 체크가 매일 초록인가

---

## 5. 컷오버 (7일 관측 통과 후 — **지금 하지 말 것**)

7일간 alarm-dispatch가 매일 성공하면 그때 별도 PR로:

1. `.github/workflows/daily_alarm.yml`의 `on: schedule:` 블록 제거
   → 저장소에 schedule 워크플로가 사라져 **60일 자동 비활성화 대상에서 벗어난다**
2. 사용하지 않는 옛 `KAKAO_REFRESH_TOKEN` 시크릿 삭제
   (현재 refresh token은 Supabase `app_secrets`에서 회전 관리 중 — Path 2)

> 관측 전에 schedule을 먼저 끄면, 외부 크론이 조용히 실패했을 때 알림이
> **완전히** 멈춘다. 순서를 지킬 것.

---

## 하지 말 것

- `alarm-dispatch.yml`에 `schedule:`을 추가하지 말 것 — 옵션 B가 제거한 바로 그
  60일 문제를 되살린다. 재가동은 외부 트리거로만.
- 관측 전 `daily_alarm.yml`의 schedule 제거 금지 (위 5번 순서 참조).
