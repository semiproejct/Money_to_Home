-- 머니 to 홈 테이블 생성 스크립트 (공식 초안 v0.2, 2026-10-11)
-- 대상: MariaDB 11.4
-- 설계 문서: docs/04_database_design.md
--
-- 실행 방법 (HeidiSQL): [파일] > [SQL 파일 불러오기]로 이 파일을 열고 F9를 누른다.
-- 여러 번 실행해도 된다. 이미 있는 표는 건너뛴다.
-- 표의 모양을 고쳤을 때는 그 표를 지운 뒤 다시 실행한다.

CREATE DATABASE IF NOT EXISTS money_to_home CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE money_to_home;

-- ------------------------------------------------------------------
-- 회원 (2차. 표는 1차에 만들고 테스트 사용자 한 줄을 넣는다)
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '번호',
  login_id         VARCHAR(20)  NOT NULL COMMENT '아이디. 영문 소문자로 시작하는 5~20자의 영문 소문자와 숫자',
  password_hash    VARCHAR(255) NOT NULL COMMENT '비밀번호 해시. 원래 값으로 되돌릴 수 없다',
  terms_agreed_at  DATETIME     NULL     COMMENT '동의한 시각. 3차',
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '가입일',
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_login_id (login_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='회원';

-- ------------------------------------------------------------------
-- 대출 상품 (1차). 두 줄. 대출 없이 계산은 상품이 아니므로 줄이 없다
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS loan_products (
  id                       INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '번호. 카드를 이 순서로 보여 준다',
  name                     VARCHAR(100) NOT NULL COMMENT '상품명',
  institution              VARCHAR(50)  NOT NULL COMMENT '취급 기관',
  max_limit                BIGINT       NOT NULL COMMENT '최대 한도. 원',
  ltv_ratio                DECIMAL(4,3) NOT NULL COMMENT '대출 비율. 70%면 0.700',
  annual_rate_pct          DECIMAL(5,3) NOT NULL COMMENT '대표 금리. 연 4.0%면 4.000',
  repayment_years_options  VARCHAR(50)  NOT NULL COMMENT '상환 기간 선택지. 10,15,20,30처럼 쉼표로 잇는다',
  max_house_price          BIGINT       NULL     COMMENT '대상 주택 가격 상한. 원. 없으면 비운다',
  eligibility_summary      VARCHAR(200) NOT NULL COMMENT '자격 조건 요약. 카드에 보인다',
  eligibility_text         TEXT         NOT NULL COMMENT '자격 조건 문구. 자세히 창에 보인다',
  base_date                DATE         NOT NULL COMMENT '기준일',
  source_url               VARCHAR(500) NOT NULL COMMENT '출처 주소',
  PRIMARY KEY (id),
  CONSTRAINT ck_loan_limit CHECK (max_limit > 0),
  CONSTRAINT ck_loan_ltv   CHECK (ltv_ratio > 0 AND ltv_ratio <= 1),
  CONSTRAINT ck_loan_rate  CHECK (annual_rate_pct >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='대출 상품';

-- ------------------------------------------------------------------
-- 재무정보, 대출 선택, 저축 계획 (1차). 회원 한 명에 한 줄
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
  id               INT UNSIGNED     NOT NULL AUTO_INCREMENT COMMENT '번호. 찜이 이 번호를 가리킨다 (2026-10-21)',
  user_id          INT UNSIGNED     NOT NULL COMMENT '회원',
  slot             TINYINT UNSIGNED NOT NULL COMMENT '칸 번호. 1, 2, 3 중 하나 (재무정보 1 ~ 3)',
  name             VARCHAR(10)      NOT NULL COMMENT '칸 이름. 1~10자',
  age              TINYINT UNSIGNED NOT NULL COMMENT '만 나이. 15~100. 계산에 쓰지 않는다',
  annual_income    BIGINT           NOT NULL COMMENT '연 소득. 원. 계산에 쓰지 않는다',
  current_assets   BIGINT           NOT NULL COMMENT '현재 보유자산. 원',
  loan_choice      ENUM('product', 'none') NULL COMMENT '대출 방법. 비어 있으면 아직 고르지 않음, none은 대출 없이 계산',
  loan_product_id  INT UNSIGNED     NULL     COMMENT '고른 상품',
  repayment_years  TINYINT UNSIGNED NULL     COMMENT '상환 기간. 년',
  monthly_saving   BIGINT           NULL     COMMENT '월 저축 가능액. 원',
  target_years     TINYINT UNSIGNED NULL     COMMENT '목표 기간. 0, 3, 5, 10 중 하나. 0은 지금',
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '처음 저장한 시각',
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일',
  selected_at      DATETIME NULL     COMMENT '시작 화면에서 이 칸을 골라 지도를 본 마지막 시각',
  PRIMARY KEY (id),
  UNIQUE KEY uq_profiles_user_slot (user_id, slot),
  KEY ix_profiles_loan_product (loan_product_id),
  CONSTRAINT fk_profiles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_profiles_loan_product FOREIGN KEY (loan_product_id) REFERENCES loan_products (id),
  CONSTRAINT ck_profiles_slot   CHECK (slot BETWEEN 1 AND 3),
  CONSTRAINT ck_profiles_name   CHECK (CHAR_LENGTH(name) BETWEEN 1 AND 10),
  CONSTRAINT ck_profiles_age    CHECK (age BETWEEN 15 AND 100),
  CONSTRAINT ck_profiles_income CHECK (annual_income BETWEEN 0 AND 10000000000),
  CONSTRAINT ck_profiles_assets CHECK (current_assets BETWEEN 0 AND 10000000000),
  CONSTRAINT ck_profiles_saving CHECK (monthly_saving IS NULL OR monthly_saving BETWEEN 0 AND 1000000000),
  CONSTRAINT ck_profiles_target CHECK (target_years IS NULL OR target_years IN (0, 3, 5, 10)),
  CONSTRAINT ck_profiles_loan   CHECK (
       (loan_choice IS NULL      AND loan_product_id IS NULL     AND repayment_years IS NULL)
    OR (loan_choice = 'none'     AND loan_product_id IS NULL     AND repayment_years IS NULL)
    OR (loan_choice = 'product'  AND loan_product_id IS NOT NULL AND repayment_years IS NOT NULL)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='재무정보';

-- ------------------------------------------------------------------
-- 아파트 (1차). 아파트 한 곳에 한 줄
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apartments (
  id              INT UNSIGNED      NOT NULL AUTO_INCREMENT COMMENT '번호',
  complex_code    VARCHAR(30)       NULL     COMMENT '단지 일련번호. 실거래가 API의 값. 확인 전에는 비운다',
  name            VARCHAR(100)      NOT NULL COMMENT '아파트명',
  gu              VARCHAR(10)       NOT NULL COMMENT '구',
  dong            VARCHAR(20)       NOT NULL COMMENT '동',
  jibun           VARCHAR(20)       NOT NULL COMMENT '지번. 506-8, 산1-9 같은 글자',
  road_address    VARCHAR(100)      NULL     COMMENT '도로명',
  built_year      SMALLINT UNSIGNED NULL     COMMENT '준공 연도',
  latitude        DECIMAL(10,7)     NULL     COMMENT '위도. 변환에 실패하면 비운다',
  longitude       DECIMAL(10,7)     NULL     COMMENT '경도',
  geocode_status  ENUM('ok', 'failed') NULL  COMMENT '좌표 변환 결과. 비어 있으면 아직 변환하지 않음',
  households      INT UNSIGNED      NULL     COMMENT '세대수. 연결되지 않으면 비운다',
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '넣은 시각',
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '고친 시각',
  PRIMARY KEY (id),
  UNIQUE KEY uq_apartments_address (gu, dong, jibun, name),
  UNIQUE KEY uq_apartments_complex_code (complex_code),
  KEY ix_apartments_lat_lng (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='아파트';

-- ------------------------------------------------------------------
-- 거래 (1차). 실거래 한 건에 한 줄
-- 겹침을 막는 열쇠가 없다. 다시 수집할 때는 그 구와 계약 연월의 거래를 지우고 넣는다
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trades (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '번호',
  apartment_id    INT UNSIGNED    NOT NULL COMMENT '아파트',
  contract_date   DATE            NOT NULL COMMENT '계약일',
  exclusive_area  DECIMAL(8,4)    NOT NULL COMMENT '전용면적. ㎡',
  price           BIGINT          NOT NULL COMMENT '거래 금액. 원',
  floor           SMALLINT        NULL     COMMENT '층',
  is_canceled     TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '해제 여부. 1이면 평균에서 뺀다',
  PRIMARY KEY (id),
  KEY ix_trades_apartment_date (apartment_id, contract_date),
  KEY ix_trades_contract_date (contract_date),
  CONSTRAINT fk_trades_apartment FOREIGN KEY (apartment_id) REFERENCES apartments (id) ON DELETE CASCADE,
  CONSTRAINT ck_trades_price CHECK (price > 0),
  CONSTRAINT ck_trades_area  CHECK (exclusive_area > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='거래';

-- ------------------------------------------------------------------
-- 면적대별 평균가 (1차). 아파트와 면적대의 조합마다 한 줄. 화면이 읽는 표
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apartment_prices (
  id                  INT UNSIGNED      NOT NULL AUTO_INCREMENT COMMENT '번호',
  apartment_id        INT UNSIGNED      NOT NULL COMMENT '아파트',
  area_band           SMALLINT UNSIGNED NOT NULL COMMENT '면적대. 전용면적의 소수점 아래를 버린 값. ㎡',
  exclusive_area      DECIMAL(8,4)      NOT NULL COMMENT '대표 전용면적. 거래에 가장 많이 나온 값. 평으로 바꿀 때 쓴다',
  supply_area         DECIMAL(7,2)      NULL     COMMENT '공급면적. ㎡. 구하지 못하면 비운다',
  supply_area_method  VARCHAR(30)       NULL     COMMENT '공급면적을 구한 방법. ledger_sum, ledger_partial, ledger_inferred, borrowed, legacy',
  avg_price           BIGINT            NOT NULL COMMENT '평균가. 원. 해제된 거래를 뺀 평균',
  min_price           BIGINT            NOT NULL COMMENT '최저가. 원',
  max_price           BIGINT            NOT NULL COMMENT '최고가. 원',
  trade_count         INT UNSIGNED      NOT NULL COMMENT '거래 건수. 해제된 거래를 뺀 수',
  period_start        DATE              NOT NULL COMMENT '집계 시작일',
  period_end          DATE              NOT NULL COMMENT '집계 종료일',
  updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '고친 시각',
  PRIMARY KEY (id),
  UNIQUE KEY uq_prices_apartment_band (apartment_id, area_band),
  KEY ix_prices_avg_price (avg_price),
  KEY ix_prices_area_band (area_band),
  CONSTRAINT fk_prices_apartment FOREIGN KEY (apartment_id) REFERENCES apartments (id) ON DELETE CASCADE,
  CONSTRAINT ck_prices_count  CHECK (trade_count >= 1),
  CONSTRAINT ck_prices_range  CHECK (min_price <= avg_price AND avg_price <= max_price),
  CONSTRAINT ck_prices_supply CHECK (supply_area IS NULL OR supply_area > exclusive_area)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='면적대별 평균가';

-- ------------------------------------------------------------------
-- 주변 시설 (3차, FR-MAP-23). 아파트와 시설 종류마다 한 줄. data/load_facilities.py가 카카오 장소 검색으로 미리 받아 넣는다
-- 서버와 화면은 카카오를 부르지 않고 이 표만 읽는다 (NFR-08). 다시 넣을 때는 전부 지우고 넣는다
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apartment_facilities (
  apartment_id  INT UNSIGNED      NOT NULL COMMENT '아파트',
  kind          VARCHAR(20)       NOT NULL COMMENT '종류. subway, school, mart, convenience, hospital, elementary, middle, high, university, bus',
  place_name    VARCHAR(100)      NULL     COMMENT '가장 가까운 곳의 이름. 반경 안에 없으면 비운다',
  distance      INT UNSIGNED      NULL     COMMENT '아파트에서 그곳까지의 직선거리. m. 지하철역은 가장 가까운 출구까지',
  exit_no       TINYINT UNSIGNED  NULL     COMMENT '지하철역의 가장 가까운 출구 번호. 출구를 못 찾으면 비우고 distance는 역까지',
  place_count   INT UNSIGNED      NOT NULL DEFAULT 0 COMMENT '반경 안의 수',
  radius        INT UNSIGNED      NOT NULL COMMENT '찾은 반경. m. 대학교만 5000, 나머지 1000',
  latitude      DECIMAL(10,7)     NULL     COMMENT '그 곳의 위도. 지하철역은 가장 가까운 출구. 반경 안에 없으면 비운다',
  longitude     DECIMAL(10,7)     NULL     COMMENT '경도',
  PRIMARY KEY (apartment_id, kind),
  CONSTRAINT fk_facilities_apartment FOREIGN KEY (apartment_id) REFERENCES apartments (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='주변 시설';

-- 10-19 오후 이전에 표를 만든 DB에 좌표 칸을 더한다 (이미 있으면 건너뛴다)
ALTER TABLE apartment_facilities ADD COLUMN IF NOT EXISTS latitude  DECIMAL(10,7) NULL COMMENT '그 곳의 위도. 지하철역은 가장 가까운 출구. 반경 안에 없으면 비운다' AFTER radius;
ALTER TABLE apartment_facilities ADD COLUMN IF NOT EXISTS longitude DECIMAL(10,7) NULL COMMENT '경도' AFTER latitude;

-- ------------------------------------------------------------------
-- 버스정류장 (3차, FR-MAP-23, 2026-10-20). 광주 5개 구의 시내버스 정류장마다 한 줄
-- data/load_facilities.py가 data/bus_stops_gwangju.csv(국토교통부 전국 버스정류장 위치정보)에서 넣는다
-- 지도가 화면 안 정류장을 A-28로 읽는다. 다시 넣을 때는 전부 지우고 넣는다
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bus_stops (
  stop_id    VARCHAR(20)    NOT NULL COMMENT '정류장 번호. 국토교통부 자료의 정류장번호 (예: KJB3908)',
  name       VARCHAR(100)   NOT NULL COMMENT '정류장 이름',
  latitude   DECIMAL(10,7)  NOT NULL COMMENT '위도',
  longitude  DECIMAL(10,7)  NOT NULL COMMENT '경도',
  PRIMARY KEY (stop_id),
  KEY ix_bus_stops_lat_lng (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='버스정류장';

-- ------------------------------------------------------------------
-- 수집 기준일 (2차). 자료를 넣을 때마다 한 줄
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_collections (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '번호',
  dataset     VARCHAR(20)  NOT NULL COMMENT '자료 종류. trades, coordinates, supply_area, households, facilities, bus_stops',
  source      VARCHAR(100) NOT NULL COMMENT '받은 곳',
  base_date   DATE         NOT NULL COMMENT '기준일',
  row_count   INT UNSIGNED NULL     COMMENT '줄 수',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '기록한 시각',
  PRIMARY KEY (id),
  KEY ix_collections_dataset_date (dataset, base_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='수집 기준일';

-- ------------------------------------------------------------------
-- 저장한 결과 (3차). 저장할 때의 조건과 결과를 복사해 둔다
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_results (
  id                       INT UNSIGNED      NOT NULL AUTO_INCREMENT COMMENT '번호',
  user_id                  INT UNSIGNED      NOT NULL COMMENT '회원',
  apartment_id             INT UNSIGNED      NULL     COMMENT '아파트. 원본이 지워지면 비워진다',
  loan_product_id          INT UNSIGNED      NULL     COMMENT '대출 상품. 원본이 지워지면 비워진다',
  profile_id               INT UNSIGNED      NULL     COMMENT '찜한 재무정보. 그 재무정보를 지우면 비워진다 (2026-10-21)',
  apartment_name           VARCHAR(100)      NOT NULL COMMENT '저장 당시 아파트명',
  gu                       VARCHAR(10)       NOT NULL COMMENT '저장 당시 구',
  dong                     VARCHAR(20)       NOT NULL COMMENT '저장 당시 동',
  area_band                SMALLINT UNSIGNED NOT NULL COMMENT '면적대',
  exclusive_area           DECIMAL(8,4)      NOT NULL COMMENT '대표 전용면적',
  supply_area              DECIMAL(7,2)      NULL     COMMENT '공급면적',
  avg_price                BIGINT            NOT NULL COMMENT '저장 당시 평균가. 원',
  current_assets           BIGINT            NOT NULL COMMENT '현재 보유자산. 원',
  monthly_saving           BIGINT            NOT NULL COMMENT '월 저축 가능액. 원',
  target_years             TINYINT UNSIGNED  NOT NULL COMMENT '목표 기간. 년',
  loan_choice              ENUM('product', 'none') NOT NULL COMMENT '대출 방법',
  loan_product_name        VARCHAR(100)      NULL     COMMENT '저장 당시 상품명',
  repayment_years          TINYINT UNSIGNED  NULL     COMMENT '상환 기간. 년',
  accumulated_saving       BIGINT            NOT NULL COMMENT '누적 저축액. 원',
  loan_amount              BIGINT            NULL     COMMENT '예상 대출금액. 원',
  monthly_payment          BIGINT            NULL     COMMENT '예상 월 상환액. 원',
  shortage                 BIGINT            NOT NULL COMMENT '부족자금. 원. 음수면 그 절댓값이 여유자금',
  required_monthly_saving  BIGINT            NULL     COMMENT '필요 월 저축액. 원',
  allowed_growth_rate      DECIMAL(5,1)      NULL     COMMENT '허용 상승률. 연 %',
  category                 ENUM('now', 'within', 'lack') NOT NULL COMMENT '구분. 지금 가능, 기간 내 가능, 자금 부족',
  created_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '저장한 시각',
  PRIMARY KEY (id),
  KEY ix_saved_user_created (user_id, created_at),
  KEY ix_saved_profile (profile_id),
  CONSTRAINT fk_saved_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_saved_apartment FOREIGN KEY (apartment_id) REFERENCES apartments (id) ON DELETE SET NULL,
  CONSTRAINT fk_saved_loan_product FOREIGN KEY (loan_product_id) REFERENCES loan_products (id) ON DELETE SET NULL,
  CONSTRAINT fk_saved_profile FOREIGN KEY (profile_id) REFERENCES profiles (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='저장한 결과';

-- ------------------------------------------------------------------
-- 1차용 테스트 사용자 (T-USER-08). 이 해시로는 로그인할 수 없다
-- ------------------------------------------------------------------
INSERT IGNORE INTO users (id, login_id, password_hash) VALUES (1, 'testuser', '!');
