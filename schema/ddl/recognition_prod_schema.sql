SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL';

CREATE SCHEMA IF NOT EXISTS `video_dev` DEFAULT CHARACTER SET utf8 COLLATE utf8_bin ;
USE `video_dev` ;

-- -----------------------------------------------------
-- Table `video_dev`.`faces`
-- -----------------------------------------------------
CREATE  TABLE IF NOT EXISTS `video_dev`.`faces` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `user_id` INT NOT NULL ,
  `contact_id` INT NOT NULL ,
  `face_id` INT NOT NULL ,
  `face_url` VARCHAR(2048) NOT NULL ,
  `external_id` INT NULL DEFAULT NULL ,
  `score` DOUBLE NOT NULL ,
  `l1_idx` VARCHAR(32) NULL DEFAULT NULL ,
  `l1_tag` VARCHAR(128) NULL DEFAULT NULL ,
  `l2_idx` VARCHAR(32) NOT NULL ,
  `l2_tag` VARCHAR(128) NOT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `user_id_UNIQUE` (`user_id` ASC, `contact_id` ASC, `face_id` ASC) )
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev`.`recognition_feedback`
-- -----------------------------------------------------
CREATE  TABLE IF NOT EXISTS `video_dev`.`recognition_feedback` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `user_id` INT(11) NOT NULL ,
  `face_url` VARCHAR(2048) NOT NULL ,
  `face1_id` INT(11) NULL DEFAULT NULL ,
  `face1_confidence` DOUBLE NULL DEFAULT NULL ,
  `face2_id` INT(11) NULL DEFAULT NULL ,
  `face2_confidence` DOUBLE NULL DEFAULT NULL ,
  `face3_id` INT(11) NULL DEFAULT NULL ,
  `face3_confidence` DOUBLE NULL DEFAULT NULL ,
  `feedback_received` TINYINT(1) NULL DEFAULT NULL ,
  `recognized` TINYINT(1) NULL DEFAULT NULL ,
  `feedback_result` INT(11) NULL DEFAULT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) )
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev`.`faces2`
-- -----------------------------------------------------
CREATE  TABLE IF NOT EXISTS `video_dev`.`faces2` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `user_id` INT NOT NULL ,
  `contact_id` INT NOT NULL ,
  `face_id` INT NOT NULL ,
  `face_url` VARCHAR(2048) NOT NULL ,
  `external_id` INT NULL DEFAULT NULL ,
  `idx` VARCHAR(32) NOT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `user_id_UNIQUE` (`user_id` ASC, `contact_id` ASC, `face_id` ASC) )
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev`.`recognition_feedback2`
-- -----------------------------------------------------
CREATE  TABLE IF NOT EXISTS `video_dev`.`recognition_feedback2` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `user_id` INT(11) NOT NULL ,
  `face_url` VARCHAR(2048) NOT NULL ,
  `face1_id` INT(11) NULL DEFAULT NULL ,
  `face1_confidence` DOUBLE NULL DEFAULT NULL ,
  `face2_id` INT(11) NULL DEFAULT NULL ,
  `face2_confidence` DOUBLE NULL DEFAULT NULL ,
  `face3_id` INT(11) NULL DEFAULT NULL ,
  `face3_confidence` DOUBLE NULL DEFAULT NULL ,
  `feedback_received` TINYINT(1) NULL DEFAULT NULL ,
  `recognized` TINYINT(1) NULL DEFAULT NULL ,
  `feedback_result` INT(11) NULL DEFAULT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) )
ENGINE = InnoDB;

USE `video_dev`;

DELIMITER $$
USE `video_dev`$$


CREATE
	TRIGGER face_created BEFORE INSERT ON faces FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev`$$


CREATE
	TRIGGER face_updated BEFORE UPDATE ON faces FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$


DELIMITER ;

DELIMITER $$
USE `video_dev`$$


CREATE
	TRIGGER recognition_feedback_created BEFORE INSERT ON recognition_feedback FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev`$$


CREATE
	TRIGGER recognition_feedback_updated BEFORE UPDATE ON recognition_feedback FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$


DELIMITER ;

DELIMITER $$
USE `video_dev`$$


CREATE
	TRIGGER face2_created BEFORE INSERT ON faces2 FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev`$$


CREATE
	TRIGGER face2_updated BEFORE UPDATE ON faces2 FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$


DELIMITER ;

DELIMITER $$
USE `video_dev`$$


CREATE
	TRIGGER recognition_feedback2_created BEFORE INSERT ON recognition_feedback2 FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev`$$


CREATE
	TRIGGER recognition_feedback2_updated BEFORE UPDATE ON recognition_feedback2 FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$


DELIMITER ;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
