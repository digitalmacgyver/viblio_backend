SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL';

CREATE SCHEMA IF NOT EXISTS `video_dev_1` DEFAULT CHARACTER SET utf8 COLLATE utf8_bin ;
USE `video_dev_1` ;

-- -----------------------------------------------------
-- Table `video_dev_1`.`faces`
-- -----------------------------------------------------
CREATE  TABLE IF NOT EXISTS `video_dev_1`.`faces` (
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

USE `video_dev_1`;

DELIMITER $$
USE `video_dev_1`$$


CREATE
	TRIGGER face_created BEFORE INSERT ON faces FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$


CREATE
	TRIGGER face_updated BEFORE UPDATE ON faces FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$


DELIMITER ;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
