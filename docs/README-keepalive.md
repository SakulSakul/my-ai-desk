# keepalive 번들 (v3.1) — 셋업 & crux 실측 절차

2차 심의(council)로 발견된 **버그 4개를 모두 반영**한 옵션 A(GitHub 내부 유지) 버전이다.
아직 옵션 B(스케줄 외재화)로 갈지 미정이라면, 아래 §7의 **미결 검증 4개**를 먼저 확인하고 결정하라.

## v3.1 변경점 (버그 수정)
1. **[버그1] 텔레그램 시크릿명 통일** — `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID`. 기존 repo(`daily_alarm.yml`·`telegram_notify.py`)와 **반드시 동일**해야 한다. 이름이 어긋나면 실패 알림이 없는 시크릿을 참조해 조용히 실패한다("조용한 실패 종료"가 주제인 번들이 조용한 실패를 심는 아이러니).
2. **[버그2] `keepalive.py` 무의존화** — supabase SDK + 매일 `pip install` 제거, stdlib `urllib` raw REST 핑으로 교체. 가디언은 지켜야 할 대상보다 단순해야 한다.
3. **[버그3] 백업 암호화를 Phase 0로** — 아래 §3. public repo 아티팩트는 진짜 프라이빗이 아니다. **업로드 전 암호화**를 Phase 0 게이트로. Phase 3로 미루면 노출은 이미 Phase 0에서 발생한다.
4. **[버그4] dead-man's switch 핑 위치 교정** — healthcheck 핑을 Supabase 핑 **직후**로 옮기고 heartbeat와 의존을 끊었다. PAT 만료로 heartbeat가 실패해도 dead-man 신호가 오염되지 않는다. dead-man은 순수하게 "cron이 돌고 Supabase 핑이 성공했는가"만 신호한다.

---

## 1. 필요한 GitHub Secrets

| 시크릿 | 용도 | 필수 |
|--------|------|------|
| `GITHUB_PAT` | heartbeat 커밋 push (사용자 활동으로 기록되게) | ★필수 |
| `SUPABASE_URL`, `SUPABASE_KEY` | Supabase 핑 | ★필수 |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | 실패 알림 (**기존 repo와 동일 이름 확인**) | 권장 |
| `HEALTHCHECK_URL` | dead-man's switch 핑 URL | ★강력 권장 |

> 착수 전 30초 체크: 기존 repo의 Settings > Secrets에서 텔레그램 시크릿의 **정확한 이름**을 눈으로 확인하고 `keepalive.yml`의 `TG_TOKEN`/`TG_CHAT` env를 거기에 맞춰라.

---

## 2. dead-man's switch — "결과"를 감시하라 (메커니즘 말고)

원리: cron이 **Supabase 핑에 성공할 때마다** 외부 모니터에 핑. cron이 죽으면 핑이 끊기고 모니터가 **당신에게** 알린다. 감시자가 감시 대상(cron) 밖에 있는 게 핵심.

- 무료: healthchecks.io, cron-job.org 등. period를 **26시간**(하루 주기 + 여유), grace 몇 시간.
- **period를 60일이 아니라 매일 핑 기준(26h)으로.** 최단 도화선은 Supabase pause(7일)이지 Actions(60일)가 아니다.
- 발급 URL을 `HEALTHCHECK_URL` 시크릿에.
- 보조(설정 0): GitHub은 스케줄 워크플로 자동 비활성화 시 관리자에게 이메일을 보낸다 — 이미 cron 밖 신호다.

> 심의 노트: 이상적으로 dead-man은 "외부 크론이 살아있나"(메커니즘)가 아니라 "Supabase 마지막 핑이 신선한가"(결과)를 봐야 한다. 이 번들은 GitHub 내부(A)라 "핑 성공 시 통지"로 근사한다. 옵션 B로 가면 이 구분이 더 중요해진다.

---

## 3. [버그3] 백업 — Phase 0부터 업로드 전 암호화

public 저장소의 Actions 아티팩트는 Actions 탭이 공개라 **다운로드 가능**하다. `tasks`/`memos`엔 업무 이력이 들어있다. 노출은 백업을 올리는 그 순간(Phase 0) 발생하므로, 암호화를 Phase 3로 미루면 늦다.

- 최소안: `pg_dump` 또는 REST export → **대칭 암호화 후** 업로드.
  ```bash
  # 예: age(권장) 또는 gpg 대칭. 키/패스프레이즈는 GitHub Secret으로.
  age -p -o backup.json.age backup.json        # 또는
  gpg --batch --symmetric --passphrase "$BACKUP_PASSPHRASE" backup.json
  ```
- 암호문만 아티팩트로 업로드. 평문은 러너에 남기지 말 것.
- 복원 리허설을 최소 1회(복호화 → import) 해봐야 "백업"이라 부를 수 있다.

---

## 4. crux 실측 — "PAT 커밋이 60일 타이머를 리셋하는가" (옵션 A 한정)

옵션 A를 유지한다면 이게 생명줄이다.
- **A. 즉시:** `workflow_dispatch`로 1회 실행 → heartbeat 커밋이 **당신 계정(봇 아님)**으로 찍히는지 확인.
- **B. 관찰:** Actions 탭에 "This scheduled workflow is disabled..." 배너 없이 계속 스케줄되는지, heartbeat 커밋이 20일마다 쌓이는지 주기 확인. 배너가 뜨거나 커밋 후에도 last activity가 갱신 안 되면 → **crux 거짓** → §7의 옵션 B 또는 유료 전환.

---

## 5. 자기참조 순환 인지 (A의 구조적 한계)

`cron 생존 → heartbeat 커밋 → cron 생존`은 닫힌 순환이다. 정상일 땐 자기유지되지만 **한 번 끊기면(PAT 만료·crux 거짓·버그) 스스로 못 살아난다** — 수동 재점화만 가능. 그래서 §2 dead-man + §6 런북이 필수다. keep-alive는 "뿌리를 자르는" 게 아니라 "관성을 유지"할 뿐이다.

---

## 6. 재점화 런북 (cron이 죽었을 때)
1. dead-man 알림 수신 → Actions 탭 확인.
2. 비활성화면 Enable + `workflow_dispatch` 수동 실행.
3. Supabase pause면 Restore.
4. 카카오 죽었으면 refresh token 재발급 + 시크릿 갱신.
5. PAT 만료면 재발급 + `GITHUB_PAT` 교체. (PAT 만료 리마인더는 cron 밖 — GitHub 만료 메일/앱 배너로.)

---

## 7. ★ 옵션 B(외재화)로 갈지 결정하기 전 — 미결 검증 4개

2차 심의 결론: 스케줄을 외부 크론으로 빼는 옵션 B는 방향이 옳지만 "crux를 없앤다"가 아니라 **다른 미지로 교환**한다. 아래를 먼저 확인하라.

1. **[최우선] `repository_dispatch`로 트리거되는 워크플로도 60일 자동비활성화 대상인가?** 대상이면 B의 crux 소멸은 환상이다.
2. **Supabase가 외부 REST 핑을 pause 방지 '활동'으로 인정하는가?** 거짓이면 A·B 둘 다 무의미.
3. **무료 크론에 dead-man/이중화가 실제로 가능한가?** 불가하면 B의 성립 조건이 깨진다.
4. **dispatch 토큰 스코프·만료 주기.** PAT 만료 SPOF는 B에서도 소멸이 아니라 이동한다.

### 대안 지형 (심의 소수의견)
- **하이브리드(A + B 병행):** `on:schedule` 유지 + 외부 크론 이중 핑. 두 스케줄러가 상호 백업 → SPOF 이동이 아니라 이중화. 개인 앱엔 다소 과하지만 가장 견고.
- **Supabase 유료 전환:** pause 자체가 사라져 최단 도화선(7일)을 소거. 월 소액으로 crux의 Supabase 축을 통째로 제거. 외부 계정·자기참조 순환 없이 가장 단순할 수 있음.

> 권고 순서: (1) 이 A 수정본으로 지금 안전하게 돌린다 → (2) 위 4개를 확인한다 → (3) 결과를 보고 A 유지 / B 외재화 / 유료 전환 중 택. 검증 전엔 A를 성급히 폐기하지 말 것.
