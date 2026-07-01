# 옵션 B — 스케줄 외재화 셋업 가이드

**목표:** GitHub Actions의 `schedule:` 크론을 버리고, 외부 무료 크론이 매일 워크플로를 트리거한다.
그러면 60일 자동 비활성화(schedule 한정)의 대상이 아예 사라지고 — heartbeat 커밋·자기참조 순환·crux가 모두 소멸한다.

구성 파일: `alarm-dispatch.yml`(schedule 없음), `keepalive.py`(stdlib urllib, 재사용).

```
외부 크론(cron-job.org)  ──매일 POST──▶  GitHub repository_dispatch API
                                              │  (event_type: daily-alarm)
                                              ▼
                                    alarm-dispatch.yml 실행
                                    ├ Supabase 핑 (7일 pause 방지)
                                    ├ 알림 발송 (telegram/kakao)
                                    └ 최종 성공 시 ──▶ healthchecks.io (dead-man)
                                                        │ 26h 내 핑 없으면
                                                        ▼  당신에게 이메일/푸시
```

---

## 1. 시크릿 (GitHub repo Settings → Secrets)

기존 것 재사용 + 하나 추가.

| 시크릿 | 용도 |
|--------|------|
| `SUPABASE_URL`, `SUPABASE_KEY` | Supabase 핑 + 알림 |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | 알림 (기존 이름 확인) |
| `KAKAO_REST_API_KEY` | 카카오 알림 |
| `SUPABASE_SERVICE_ROLE_KEY` | app_secrets(카카오 토큰) 읽기/쓰기 — **kakao 스텝에만 주입** |
| `HEALTHCHECK_CRON_URL` | dead-man (A) "cron 생존" 핑 URL |
| `HEALTHCHECK_SENT_URL` | dead-man (B) "알림 전송" 핑 URL |

> **Path 2:** 카카오 refresh token은 GitHub Secret이 아니라 Supabase `app_secrets`에 회전 저장되므로 `KAKAO_REFRESH_TOKEN`·`GITHUB_PAT`(Secrets:write)가 더 이상 필요 없다. 대신 `SUPABASE_SERVICE_ROLE_KEY`가 kakao 스텝에 들어간다(전체 DB 우회 키 — 로그 마스킹·액션 SHA 핀으로 유출 방어).
>
> **dead-man 2개:** (A)는 Supabase 핑 직후 = "cron 살아있음"만, (B)는 알림 전송 성공 후 = "알림 실제로 나감". (B)가 며칠 결번이면 "핑은 오는데 알림이 안 온다"를 잡는다. healthchecks.io에서 체크 2개를 만들어 각 URL을 해당 시크릿에.

---

## 2. dead-man 설정 (healthchecks.io, 무료, 5분)

이게 2차 심의가 지적한 "204 = 접수일 뿐 성공 아님" 간극을 닫는 **역방향 엣지**다.

1. healthchecks.io에서 Check 생성. **Period 1 day, Grace 2 hours** 정도.
2. 발급된 ping URL을 `HEALTHCHECK_URL` 시크릿에 저장.
3. `alarm-dispatch.yml`의 마지막 성공 스텝이 이 URL을 때린다. 워크플로가 **끝까지 성공**해야만 핑이 가므로, 크론 미발화·dispatch 실패·중간 스텝 실패가 전부 "핑 부재"로 잡힌다.

> 왜 GitHub 실패 알림(`if:failure()`)만으로 부족한가: `if:failure()`는 "워크플로가 돌다가 실패"만 잡는다. "크론이 아예 안 쐈다 / dispatch가 401로 튕겼다"는 워크플로가 시작조차 안 하므로 failure 스텝도 안 돈다. healthchecks의 침묵 감지만이 이걸 잡는다.

---

## 3. 외부 크론 설정 (cron-job.org, 무료)

매일 GitHub `repository_dispatch` API를 호출하는 잡 하나.

- **URL:** `https://api.github.com/repos/SakulSakul/my-ai-desk/dispatches`
- **Method:** `POST`
- **Headers:**
  - `Authorization: Bearer <FINE_GRAINED_PAT>`
  - `Accept: application/vnd.github+json`
  - `X-GitHub-Api-Version: 2022-11-28`
- **Body:** `{"event_type":"daily-alarm"}`
- **Schedule:** 원하는 시각(예: 매일 KST 06:17 → 서버 타임존 확인해 설정).
- **실패 알림 켜기:** cron-job.org는 응답이 2xx가 아니면(예: PAT 만료로 401) 이메일 알림을 준다 → 켜둘 것. (dead-man과 이중.)

### PAT (fine-grained) 권한
- 이 repo 하나로 스코프.
- **Repository permission → Contents: Read and write** (repository_dispatch 이벤트 생성에 필요. 토큰 발급 UI에서 dispatches가 어느 권한에 묶이는지 한 번 확인할 것.)
- **만료 1년 + 리마인더는 cron 밖 채널로.** PAT 만료는 B에 남는 유일한 크레덴셜 SPOF다. GitHub의 토큰 만료 이메일 알림을 켜두고, 만료일을 캘린더에 박아라. (cron 안에서 리마인더를 돌리면 그게 죽을 때 리마인더도 죽는 순환.)

정상 응답은 **204 No Content**다. 이건 "이벤트 접수"이지 "워크플로 성공"이 아님을 기억하라 — 성공 증명은 §2 dead-man이 한다.

---

## 4. 마이그레이션 절차 (★ 순서 중요)

1. `keepalive.py`, `alarm-dispatch.yml`을 repo에 추가하고 main에 머지. (기존 알림은 아직 건드리지 않음 — 둘이 잠시 병행)
2. §1 시크릿(HEALTHCHECK_URL) 추가, §2 healthchecks 생성, §3 외부 크론 생성.
3. **수동 검증:** GitHub Actions 탭에서 `alarm-dispatch`를 `workflow_dispatch`로 1회 실행 → 알림이 오는지 + healthchecks에 핑이 찍히는지 확인. 이어 외부 크론에서 "Run now"로 dispatch가 워크플로를 실제로 띄우는지 확인.
4. **양쪽 다 확인되면 — 기존 스케줄 알림을 끈다.** `daily_alarm.yml`에서 `on: schedule:` 블록을 **제거**(파일 자체를 지우거나 트리거만 삭제). ★ 이 단계를 빼먹고 schedule을 남기면, 그 파일이 60일 뒤 비활성화될 때 문제가 재발한다. B의 핵심 조건은 "schedule을 완전히 없앤다"이다.
5. 며칠간 외부 크론 → 알림 → healthchecks가 매일 도는지 관찰.

**롤백:** 문제가 생기면 `daily_alarm.yml`의 schedule을 되살리고 외부 크론을 일시정지하면 즉시 원상복귀. (그래서 4단계 전까지 병행 유지.)

---

## 5. 남는 리스크 (정직하게)

- **dispatch PAT 만료** — B의 유일한 크레덴셜 SPOF. §3의 이중 알림(cron-job.org 401 알림 + dead-man 침묵)으로 조기 감지. 폭발반경은 A의 PAT보다 작다(Contents만, push 없음).
- **외부 크론 서비스 지속성** — 무료 티어 정책 변경·계정 휴면. 걱정되면 두 번째 무료 크론(healthchecks.io도 cron 트리거 가능, 또는 UptimeRobot)으로 이중화.
- **Supabase 핑 대상** — `keepalive.py`가 실테이블 SELECT(`/rest/v1/tasks?select=id&limit=1`)를 하므로 활동으로 인정된다. API 루트만 치도록 바꾸지 말 것.
- **사용 공백** — 매일 쓰면 방문이 7일 pause를 방어하지만, 7일 넘는 공백(여행 등)엔 이 핑이 유일한 방어다. 그래서 핑을 유지한다.

---

## 6. 이 구성이 A 대비 얻는 것

- **crux(PAT heartbeat가 60일 타이머를 리셋하는가) 소멸** — schedule이 없으니 60일 타이머 자체가 없다. 검증 불가 가정 제거.
- **자기참조 순환 소멸** — 외부에서 트리거되는 DAG. "죽으면 스스로 못 깨어남" 결함이 사라진다(외부 크론이 깨움).
- **Streamlit 재배포 churn 0** — heartbeat 커밋이 없다.
- **PAT 스코프 축소** — 워크플로가 push를 안 해 Contents:write 부담이 외부 크론 쪽 dispatch 권한으로 국한.
