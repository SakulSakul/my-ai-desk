-- app_secrets.sql — 회전 시크릿(카카오 refresh token 등) 저장 테이블 [Path 2, 심의 수정본]
-- Supabase 대시보드 → SQL Editor 에서 1회 실행.
--
-- ★ 이 파일에는 실제 토큰을 넣지 말 것. 실토큰을 붙여 커밋하면 git 히스토리에 영구 유출된다.
--   시드(토큰 주입)는 아래 주석의 문장을 '콘솔에서만' 직접 실행한다(파일엔 남기지 않는다).
--
-- 보안 모델:
--   RLS 켜고 정책을 하나도 만들지 않음 = anon / authenticated 로는 행 접근 전부 거부.
--   추가로 테이블 권한 자체를 anon/authenticated 에서 REVOKE(정책 부재에만 의존하지 않도록 이중 방어).
--   service_role 키만 RLS 를 우회해 읽고 쓸 수 있음(= GitHub Actions 의 kakao 스텝에서만 사용).
--   ※ service_role 은 전체 DB 를 우회하는 강력 키다. CI 로그 마스킹·액션 SHA 핀으로 유출을 막을 것.

create table if not exists app_secrets (
  key        text primary key,
  value      text not null,
  updated_at timestamptz not null default now()
);

alter table app_secrets enable row level security;

-- 정책 부재(기본 거부)에 더해, 테이블 권한을 명시적으로 회수(방어 심층화).
revoke all on table app_secrets from anon, authenticated;

-- 배포 후 실측 권장: anon 키로 아래가 '거부/빈결과'인지 확인.
--   curl "$SUPABASE_URL/rest/v1/app_secrets?select=*" -H "apikey: <ANON_KEY>" -H "Authorization: Bearer <ANON_KEY>"

-- ─────────────────────────────────────────────────────────────
-- 시드(최초 1회) — 아래 문장을 'Supabase 콘솔 SQL Editor 에서만' 실행. 이 파일에 토큰을 채워 커밋하지 말 것.
-- insert into app_secrets (key, value)
-- values ('kakao_refresh_token', '<콘솔에서만 붙여넣기 — 커밋 금지>')
-- on conflict (key) do update set value = excluded.value, updated_at = now();
-- ─────────────────────────────────────────────────────────────
