-- 재무정보 3개 + 찜한 재무정보 (2026-10-21). 담당: 박채은
-- 대상: 이미 db/schema.sql로 표를 만들어 쓰고 있는 MariaDB 11.4
-- 설계 문서: docs/04_database_design.md 3.2, 3.8, 4장
--
-- 하는 일
--   1. profiles: 회원 한 명에 한 줄 → 3줄까지. id(새 기본키), slot(칸 번호), name(이름), selected_at을 더한다.
--      지금 있는 줄은 모두 "재무정보 1"(slot 1)이 된다. 값은 그대로다.
--   2. saved_results: profile_id(찜한 재무정보)를 더한다. 지금 있는 찜은 그 회원의 재무정보 1에 잇는다.
--
-- 실행 방법 (HeidiSQL): [파일] > [SQL 파일 불러오기]로 이 파일을 열고 F9를 누른다. 한 번만 실행한다.
-- 표를 새로 만드는 경우(빈 DB)에는 이 파일이 필요 없다. db/schema.sql에 이미 들어 있다.
-- 실행 전에 profiles에 id 칸이 있으면 이미 옮긴 것이다. 다시 실행하지 않는다.

USE money_to_home;

-- ------------------------------------------------------------------
-- 1. profiles
-- ------------------------------------------------------------------
-- user_id가 기본키였으므로 외래키를 잠시 풀고 기본키를 바꾼다.
ALTER TABLE profiles DROP FOREIGN KEY fk_profiles_user;

ALTER TABLE profiles
  DROP PRIMARY KEY,
  ADD COLUMN id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '번호. 찜이 이 번호를 가리킨다 (2026-10-21)' FIRST,
  ADD PRIMARY KEY (id),
  ADD COLUMN slot TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '칸 번호. 1, 2, 3 중 하나 (재무정보 1 ~ 3)' AFTER user_id,
  ADD COLUMN name VARCHAR(10) NOT NULL DEFAULT '재무정보 1' COMMENT '칸 이름. 1~10자' AFTER slot,
  ADD COLUMN selected_at DATETIME NULL COMMENT '시작 화면에서 이 칸을 골라 지도를 본 마지막 시각' AFTER updated_at,
  ADD UNIQUE KEY uq_profiles_user_slot (user_id, slot),
  ADD CONSTRAINT ck_profiles_slot CHECK (slot BETWEEN 1 AND 3),
  ADD CONSTRAINT ck_profiles_name CHECK (CHAR_LENGTH(name) BETWEEN 1 AND 10);

-- 기본값은 옮기는 동안만 쓴다. 새 줄은 서버가 칸 번호와 이름을 정해서 넣는다.
ALTER TABLE profiles
  ALTER COLUMN slot DROP DEFAULT,
  ALTER COLUMN name DROP DEFAULT;

ALTER TABLE profiles
  ADD CONSTRAINT fk_profiles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;

-- ------------------------------------------------------------------
-- 2. saved_results
-- ------------------------------------------------------------------
ALTER TABLE saved_results
  ADD COLUMN profile_id INT UNSIGNED NULL COMMENT '찜한 재무정보. 그 재무정보를 지우면 비워진다 (2026-10-21)' AFTER loan_product_id,
  ADD KEY ix_saved_profile (profile_id),
  ADD CONSTRAINT fk_saved_profile FOREIGN KEY (profile_id) REFERENCES profiles (id) ON DELETE SET NULL;

-- 지금까지의 찜은 그 회원의 재무정보 1로 찜한 것으로 둔다.
UPDATE saved_results s
JOIN profiles p ON p.user_id = s.user_id AND p.slot = 1
SET s.profile_id = p.id
WHERE s.profile_id IS NULL;

-- 확인: 아래 두 줄의 결과를 본다.
-- SHOW CREATE TABLE profiles;
-- SELECT COUNT(*) AS 찜, COUNT(profile_id) AS 재무정보가_이어진_찜 FROM saved_results;
