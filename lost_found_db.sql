
-- 0) CREATE DATABASE (fresh reset)

DROP DATABASE IF EXISTS lost_found_db;
CREATE DATABASE lost_found_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lost_found_db;

SET sql_mode = 'STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION';

-- 1) USER TABLE (with admin + timestamps)

CREATE TABLE User (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    contact_number VARCHAR(15),
    password VARCHAR(255) NOT NULL,
    branch VARCHAR(50),
    semester INT,
    address_street VARCHAR(150),
    address_city VARCHAR(100),
    address_pincode VARCHAR(10),

    is_admin TINYINT(1) NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP 
                  ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_branch_sem ON User(branch, semester);


-- 2) LOST_ITEM TABLE 
CREATE TABLE Lost_Item (
    lost_id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    date_lost DATE NOT NULL,
    location_lost ENUM('Library','Canteen','Hostel','Classroom','Playground','Lab','Other') NOT NULL,
    image_path VARCHAR(255),

    user_id INT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP 
                  ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_lost ON Lost_Item(category, date_lost, location_lost);


-- 3) FOUND_ITEM TABLE (with image upload)

CREATE TABLE Found_Item (
    found_id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    date_found DATE NOT NULL,
    location_found ENUM('Library','Canteen','Hostel','Classroom','Playground','Lab','Other') NOT NULL,
    status ENUM('unclaimed','claimed','pending') NOT NULL DEFAULT 'unclaimed',
    image_path VARCHAR(255),

    user_id INT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP 
                  ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_found ON Found_Item(category, date_found, location_found, status);


-- 4) CLAIM TABLE 
CREATE TABLE Claim (
    claim_id INT AUTO_INCREMENT PRIMARY KEY,
    claimant_name VARCHAR(100) NOT NULL,
    proof_document VARCHAR(255),
    claim_status ENUM('pending','approved','rejected') DEFAULT 'pending',
    found_id INT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP 
                  ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (found_id) REFERENCES Found_Item(found_id) ON DELETE CASCADE
);

CREATE INDEX idx_claim ON Claim(found_id, claim_status);


-- 5) MATCH RECORD TABLE 
CREATE TABLE Match_Record (
    match_id INT AUTO_INCREMENT PRIMARY KEY,
    lost_id INT NOT NULL,
    found_id INT NOT NULL,
    status ENUM('matched','not_matched','pending') DEFAULT 'matched',
    matched_date DATE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP 
                  ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (lost_id) REFERENCES Lost_Item(lost_id) ON DELETE CASCADE,
    FOREIGN KEY (found_id) REFERENCES Found_Item(found_id) ON DELETE CASCADE,

    CONSTRAINT uq_match UNIQUE(lost_id, found_id)
);

CREATE INDEX idx_match ON Match_Record(status, matched_date);

-- 6) TRIGGERS: AUTO MATCH LOST <-> FOUND


DELIMITER $$

--  Trigger: When a FOUND item is inserted → try to match a LOST item
DROP TRIGGER IF EXISTS auto_match_found $$
CREATE TRIGGER auto_match_found
AFTER INSERT ON Found_Item
FOR EACH ROW
BEGIN
    DECLARE v_lost_id INT;

    SELECT lost_id INTO v_lost_id
    FROM Lost_Item
    WHERE category = NEW.category
      AND location_lost = NEW.location_found
      AND ABS(DATEDIFF(NEW.date_found, date_lost)) <= 2
    ORDER BY date_lost DESC
    LIMIT 1;

    IF v_lost_id IS NOT NULL THEN
        INSERT IGNORE INTO Match_Record(lost_id, found_id, status, matched_date)
        VALUES(v_lost_id, NEW.found_id, 'matched', CURDATE());
    END IF;
END $$
    

--  Trigger: When a LOST item is inserted → try to match a FOUND item
DROP TRIGGER IF EXISTS auto_match_lost $$
CREATE TRIGGER auto_match_lost
AFTER INSERT ON Lost_Item
FOR EACH ROW
BEGIN
    DECLARE v_found_id INT;

    SELECT found_id INTO v_found_id
    FROM Found_Item
    WHERE category = NEW.category
      AND location_found = NEW.location_lost
      AND ABS(DATEDIFF(date_found, NEW.date_lost)) <= 2
    ORDER BY date_found DESC
    LIMIT 1;

    IF v_found_id IS NOT NULL THEN
        INSERT IGNORE INTO Match_Record(lost_id, found_id, status, matched_date)
        VALUES(NEW.lost_id, v_found_id, 'matched', CURDATE());
    END IF;
END $$

DELIMITER ;



-- 7) OPTIONAL VIEW: for admin reporting

CREATE VIEW v_matches_detailed AS
SELECT
    mr.match_id,
    mr.status AS match_status,
    mr.matched_date,
    l.category AS lost_category,
    l.description AS lost_description,
    l.date_lost,
    l.location_lost,
    f.description AS found_description,
    f.date_found,
    f.location_found,
    f.status AS found_status
FROM Match_Record mr
JOIN Lost_Item l ON mr.lost_id = l.lost_id
JOIN Found_Item f ON mr.found_id = f.found_id
ORDER BY mr.matched_date DE
-
INSERT INTO User
(name, email, contact_number, password, branch, semester, address_street, address_city, address_pincode, is_admin)
VALUES
('Admin', 'admin@uvce.edu', '0000000000', 'admin123', 'AIML', 8, 'Campus', 'Bengaluru', '560001', 1);


INSERT INTO User
(name, email, contact_number, password, branch, semester, address_street, address_city, address_pincode, is_admin)
VALUES
('Demo User', 'demo@uvce.edu', '9999999999', 'demo123', 'AIML', 5, 'UVCE Road', 'Bengaluru', '560001', 0);
