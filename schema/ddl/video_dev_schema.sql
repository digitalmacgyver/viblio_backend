-- ---
-- Table 'video'
-- 
-- ---

use video_dev;

-- DROP TABLE IF EXISTS `video`;
		
CREATE TABLE `video` (
  `id` INT NOT NULL AUTO_INCREMENT DEFAULT NULL,
  `owner_id` INTEGER NULL DEFAULT NULL,
  `title` VARCHAR(400) NULL DEFAULT NULL,
  `filename` VARCHAR(1024) NULL DEFAULT NULL,
  `description` VARCHAR(4000) NULL DEFAULT NULL,
  `lat` DECIMAL(11,8) NULL DEFAULT NULL,
  `lng` DECIMAL(11,8) NULL DEFAULT NULL,
  `recording_date` DATETIME NULL DEFAULT NULL,
  `created` DATETIME NOT NULL,
  PRIMARY KEY (`id`)
);

-- ---
-- Table 'image'
-- 
-- ---

-- DROP TABLE IF EXISTS `image`;
		
CREATE TABLE `image` (
  `id` INT NOT NULL AUTO_INCREMENT DEFAULT NULL,
  `video_encoding_id` INT NOT NULL,
  `video_id` INT NULL DEFAULT NULL,
  `time_stamp` DECIMAL(14,6) NOT NULL,
  `url` VARCHAR(2000) NOT NULL DEFAULT 'NULL',
  `metadata_url` VARCHAR(2000) NULL DEFAULT NULL,
  `format` VARCHAR(40) NULL DEFAULT NULL,
  `width` INT NULL DEFAULT NULL,
  `height` INT NULL DEFAULT NULL,
  `created` DATETIME NOT NULL,
  PRIMARY KEY (`id`)
);

-- ---
-- Table 'video_encoding'
-- 
-- ---

-- DROP TABLE IF EXISTS `video_encoding`;
		
CREATE TABLE `video_encoding` (
  `id` INT NULL AUTO_INCREMENT DEFAULT NULL,
  `video_id` INT NOT NULL,
  `url` VARCHAR(2000) NULL DEFAULT NULL,
  `metadata_url` VARCHAR(2000) NULL DEFAULT NULL,
  `format` VARCHAR(12) NULL DEFAULT NULL,
  `type` VARCHAR(40) NULL DEFAULT NULL,
  `hash` VARCHAR(1024) NULL DEFAULT NULL,
  `length` DECIMAL(14,6) NULL DEFAULT NULL,
  `width` INT NULL DEFAULT NULL,
  `height` INT NULL DEFAULT NULL,
  `created` DATETIME NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY (`id`, `video_id`)
);

-- ---
-- Foreign Keys 
-- ---

ALTER TABLE `video_encoding` ADD FOREIGN KEY (video_id) REFERENCES `video` (`id`);
ALTER TABLE `image` ADD FOREIGN KEY (video_encoding_id, video_id) REFERENCES `video_encoding` (`id`, `video_id`);


-- ---
-- Table Properties
-- ---

ALTER TABLE `video` ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
ALTER TABLE `image` ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
ALTER TABLE `video_encoding` ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

DELIMITER |
CREATE
	TRIGGER video_created BEFORE INSERT ON video FOR EACH ROW
BEGIN
	set NEW.created = NOW();
END;
|
DELIMITER |
CREATE
	TRIGGER video_encoding_created BEFORE INSERT ON video_encoding FOR EACH ROW
BEGIN
	set NEW.created = NOW();
END;
|
DELIMITER |
CREATE
	TRIGGER image_created BEFORE INSERT ON image FOR EACH ROW
BEGIN
	set NEW.created = NOW();
END;
|
DELIMITER ;


-- ---
-- Test Data
-- ---

-- INSERT INTO `video` (`id`,`owner_id`,`title`,`filename`,`description`,`lat`,`long`,`recording_date`,`created`) VALUES
-- ('','','','','','','','','');
-- INSERT INTO `image` (`id`,`video_encoding_id`,`video_id`,`time_stamp`,`url`,`metadata_url`,`format`,`width`,`height`,`created`) VALUES
-- ('','','','','','','','','','');
-- INSERT INTO `video_encoding` (`id`,`video_id`,`url`,`metadata_url`,`format`,`type`,`hash`,`length`,`width`,`height`,`created`) VALUES
-- ('','','','','','','','','','','');
