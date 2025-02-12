CREATE TABLE bkgsession (
  bkg_date DATE,
  bkg_time TIME,
  slot_limit INTEGER DEFAULT 5,
  primary key (bkg_date, bkg_time)
 );

CREATE TABLE booking (
  phone VARCHAR(255),
  email VARCHAR(255),
  family_name VARCHAR(255),
  bkg_date DATE NOT NULL,
  bkg_time TIME NOT NULL,
  table_num INTEGER DEFAULT 1,
  ref_num VARCHAR(255) NOT NULL,
  PRIMARY KEY (ref_num)
);