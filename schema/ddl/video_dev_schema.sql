SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

CREATE SCHEMA IF NOT EXISTS `video_dev_1` DEFAULT CHARACTER SET utf8 COLLATE utf8_bin ;
USE `video_dev_1` ;

-- -----------------------------------------------------
-- Table `video_dev_1`.`providers`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`providers` (
  `provider` VARCHAR(16) NOT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`provider`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`user_types`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`user_types` (
  `type` VARCHAR(32) NOT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`type`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media_types`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media_types` (
  `type` VARCHAR(16) NOT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`type`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `uuid` VARCHAR(36) NOT NULL,
  `media_type` VARCHAR(16) NOT NULL,
  `is_album` TINYINT(1) NOT NULL DEFAULT false,
  `title` VARCHAR(200) NULL DEFAULT NULL,
  `filename` VARCHAR(1024) NULL DEFAULT NULL,
  `description` VARCHAR(1024) NULL DEFAULT NULL,
  `recording_date` DATETIME NULL DEFAULT NULL,
  `view_count` INT NULL DEFAULT NULL,
  `lat` DECIMAL(11,8) NULL DEFAULT NULL,
  `lng` DECIMAL(11,8) NULL DEFAULT NULL,
  `geo_city` VARCHAR(128) NULL DEFAULT NULL,
  `geo_address` VARCHAR(256) NULL DEFAULT NULL,
  `status` VARCHAR(32) NULL DEFAULT NULL,
  `is_viblio_created` TINYINT(1) NOT NULL DEFAULT false,
  `skip_faces` TINYINT(1) NOT NULL DEFAULT false,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`, `user_id`),
  INDEX `fk_media_media_types1_idx` (`media_type` ASC),
  UNIQUE INDEX `uuid_UNIQUE` (`uuid` ASC),
  INDEX `fk_media_users1_idx` (`user_id` ASC),
  CONSTRAINT `fk_media_media_types1`
    FOREIGN KEY (`media_type`)
    REFERENCES `video_dev_1`.`media_types` (`type`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`users`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`users` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NOT NULL,
  `provider` VARCHAR(16) NULL DEFAULT NULL,
  `provider_id` VARCHAR(45) NULL DEFAULT NULL,
  `password` VARCHAR(128) NULL DEFAULT NULL,
  `email` VARCHAR(256) NULL DEFAULT NULL,
  `displayname` VARCHAR(128) NULL DEFAULT NULL,
  `active` VARCHAR(32) NULL DEFAULT NULL,
  `confirmed` TINYINT(1) NULL DEFAULT false,
  `accepted_terms` TINYINT(1) NULL DEFAULT NULL,
  `api_key` VARCHAR(128) NULL DEFAULT NULL,
  `metadata` TEXT NULL DEFAULT NULL,
  `user_type` VARCHAR(32) NULL DEFAULT 'individual',
  `banner_uuid` VARCHAR(36) NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_users_providers1` (`provider` ASC),
  UNIQUE INDEX `uuid_UNIQUE` (`uuid` ASC),
  INDEX `fk_users_user_types1_idx` (`user_type` ASC),
  INDEX `fk_users_media1_idx` (`banner_uuid` ASC),
  CONSTRAINT `fk_users_providers`
    FOREIGN KEY (`provider`)
    REFERENCES `video_dev_1`.`providers` (`provider`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT `fk_users_user_types1`
    FOREIGN KEY (`user_type`)
    REFERENCES `video_dev_1`.`user_types` (`type`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT `fk_users_media1`
    FOREIGN KEY (`banner_uuid`)
    REFERENCES `video_dev_1`.`media` (`uuid`)
    ON DELETE SET NULL
    ON UPDATE SET NULL)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`feature_types`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`feature_types` (
  `type` VARCHAR(16) NOT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`type`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`contacts`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`contacts` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `is_group` TINYINT(1) NOT NULL DEFAULT false,
  `contact_name` VARCHAR(128) NULL DEFAULT NULL,
  `contact_email` VARCHAR(128) NULL DEFAULT NULL,
  `contact_viblio_id` INT(11) NULL DEFAULT NULL,
  `provider` VARCHAR(16) NULL DEFAULT NULL,
  `provider_id` VARCHAR(45) NULL DEFAULT NULL,
  `picture_uri` VARCHAR(2048) NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_contacts_providers1_idx` (`provider` ASC),
  INDEX `fk_contacts_users1_idx` (`user_id` ASC),
  INDEX `fk_contacts_users2_idx` (`contact_viblio_id` ASC),
  UNIQUE INDEX `uuid_UNIQUE` (`uuid` ASC),
  CONSTRAINT `fk_contacts_providers1`
    FOREIGN KEY (`provider`)
    REFERENCES `video_dev_1`.`providers` (`provider`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT `fk_contacts_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_contacts_users2`
    FOREIGN KEY (`contact_viblio_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE SET NULL
    ON UPDATE SET NULL)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`asset_types`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`asset_types` (
  `type` VARCHAR(32) NOT NULL,
  `created_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  PRIMARY KEY (`type`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media_assets`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media_assets` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `media_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `uuid` VARCHAR(36) NOT NULL,
  `unique_hash` VARCHAR(32) NULL DEFAULT NULL,
  `asset_type` VARCHAR(32) NOT NULL,
  `mimetype` VARCHAR(40) NULL DEFAULT NULL,
  `uri` TEXT NULL DEFAULT NULL,
  `location` VARCHAR(28) NOT NULL DEFAULT 'us',
  `duration` DECIMAL(14,6) NULL DEFAULT NULL,
  `timecode` DECIMAL(14,6) NULL DEFAULT NULL,
  `face_score` DECIMAL(14,6) NULL DEFAULT NULL,
  `blur_score` DECIMAL(14,6) NULL DEFAULT NULL,
  `cv_metrics` TEXT NULL DEFAULT NULL,
  `bytes` INT(11) NULL DEFAULT NULL,
  `width` INT NULL DEFAULT NULL,
  `height` INT NULL DEFAULT NULL,
  `metadata_uri` TEXT NULL DEFAULT NULL,
  `provider` VARCHAR(16) NULL DEFAULT NULL,
  `provider_id` VARCHAR(45) NULL DEFAULT NULL,
  `view_count` INT NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`, `media_id`, `user_id`),
  INDEX `fk_media_assets_providers1_idx` (`provider` ASC),
  INDEX `fk_media_assets_asset_types1_idx` (`asset_type` ASC),
  UNIQUE INDEX `uuid_UNIQUE` (`uuid` ASC),
  INDEX `fk_media_assets_media1_idx` (`media_id` ASC, `user_id` ASC),
  UNIQUE INDEX `unique_hash_UNIQUE` (`unique_hash` ASC, `user_id` ASC),
  CONSTRAINT `fk_media_assets_providers1`
    FOREIGN KEY (`provider`)
    REFERENCES `video_dev_1`.`providers` (`provider`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_assets_asset_types1`
    FOREIGN KEY (`asset_type`)
    REFERENCES `video_dev_1`.`asset_types` (`type`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_assets_media1`
    FOREIGN KEY (`media_id` , `user_id`)
    REFERENCES `video_dev_1`.`media` (`id` , `user_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media_asset_features`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media_asset_features` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `media_asset_id` INT(11) NOT NULL,
  `media_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `feature_type` VARCHAR(16) NOT NULL,
  `coordinates` TEXT NULL DEFAULT NULL,
  `contact_id` INT(11) NULL DEFAULT NULL,
  `detection_confidence` DECIMAL(9,6) NULL DEFAULT NULL,
  `recognition_confidence` DECIMAL(9,6) NULL DEFAULT NULL,
  `track_id` INT(11) NULL DEFAULT NULL,
  `recognition_result` VARCHAR(32) NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  INDEX `fk_media_asset_features_feature_types1_idx` (`feature_type` ASC),
  INDEX `fk_media_asset_features_contacts1_idx` (`contact_id` ASC),
  PRIMARY KEY (`id`, `media_asset_id`, `media_id`, `user_id`),
  INDEX `fk_media_asset_features_media_assets1_idx` (`media_asset_id` ASC, `media_id` ASC, `user_id` ASC),
  CONSTRAINT `fk_media_asset_features_feature_types1`
    FOREIGN KEY (`feature_type`)
    REFERENCES `video_dev_1`.`feature_types` (`type`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_asset_features_contacts1`
    FOREIGN KEY (`contact_id`)
    REFERENCES `video_dev_1`.`contacts` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_asset_features_media_assets1`
    FOREIGN KEY (`media_asset_id` , `media_id` , `user_id`)
    REFERENCES `video_dev_1`.`media_assets` (`id` , `media_id` , `user_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media_comments`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media_comments` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NOT NULL,
  `media_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `comment` VARCHAR(2048) NULL DEFAULT NULL,
  `comment_number` INT NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_media_comments_users1_idx` (`user_id` ASC),
  INDEX `fk_media_comments_media1_idx` (`media_id` ASC),
  UNIQUE INDEX `uuid_UNIQUE` (`uuid` ASC),
  CONSTRAINT `fk_media_comments_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_comments_media1`
    FOREIGN KEY (`media_id`)
    REFERENCES `video_dev_1`.`media` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`share_types`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`share_types` (
  `type` VARCHAR(16) NOT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`type`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media_shares`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media_shares` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NULL DEFAULT NULL,
  `media_id` INT(11) NOT NULL,
  `user_id` INT(11) NULL DEFAULT NULL,
  `contact_id` INT(11) NULL DEFAULT NULL,
  `share_type` VARCHAR(16) NOT NULL,
  `is_group_share` TINYINT(1) NOT NULL DEFAULT false,
  `view_count` INT NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  INDEX `fk_media_shares_users1_idx` (`user_id` ASC),
  INDEX `fk_media_shares_share_types1_idx` (`share_type` ASC),
  PRIMARY KEY (`id`),
  INDEX `fk_media_shares_media1_idx` (`media_id` ASC),
  UNIQUE INDEX `uuid_UNIQUE` (`uuid` ASC),
  INDEX `fk_media_shares_contacts1_idx` (`contact_id` ASC),
  CONSTRAINT `fk_media_shares_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_shares_share_types1`
    FOREIGN KEY (`share_type`)
    REFERENCES `video_dev_1`.`share_types` (`type`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_shares_media1`
    FOREIGN KEY (`media_id`)
    REFERENCES `video_dev_1`.`media` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_shares_contacts1`
    FOREIGN KEY (`contact_id`)
    REFERENCES `video_dev_1`.`contacts` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`sessions`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`sessions` (
  `id` CHAR(72) NOT NULL,
  `session_data` TEXT NULL,
  `expires` VARCHAR(45) NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`roles`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`roles` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `role` VARCHAR(16) NOT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`pending_users`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`pending_users` (
  `email` VARCHAR(128) NOT NULL,
  `password` VARCHAR(128) NULL,
  `username` VARCHAR(128) NULL,
  `code` TEXT NULL,
  `active` VARCHAR(32) NULL,
  `created_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  PRIMARY KEY (`email`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`password_resets`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`password_resets` (
  `email` VARCHAR(128) NOT NULL,
  `code` TEXT NULL,
  `created_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  PRIMARY KEY (`email`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`user_roles`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`user_roles` (
  `user_id` INT NOT NULL,
  `role_id` INT(11) NOT NULL,
  PRIMARY KEY (`user_id`, `role_id`),
  INDEX `fk_users_roles1` (`role_id` ASC),
  CONSTRAINT `fk_user_roles_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_user_roles_roles1`
    FOREIGN KEY (`role_id`)
    REFERENCES `video_dev_1`.`roles` (`id`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`profiles`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`profiles` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `image` MEDIUMBLOB NULL,
  `image_mimetype` VARCHAR(40) NULL,
  `image_size` INT(11) NULL,
  `created_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_profiles_users1_idx` (`user_id` ASC),
  CONSTRAINT `fk_profiles_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`profile_fields`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`profile_fields` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `profiles_id` INT NOT NULL,
  `name` VARCHAR(1024) NULL,
  `value` VARCHAR(1024) NULL,
  `public` TINYINT(1) NULL DEFAULT 0,
  `created_date` DATETIME NULL,
  `updated_date` VARCHAR(45) NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_profile_fields_profiles1_idx` (`profiles_id` ASC),
  CONSTRAINT `fk_profile_fields_profiles1`
    FOREIGN KEY (`profiles_id`)
    REFERENCES `video_dev_1`.`profiles` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`links`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`links` (
  `id` INT NOT NULL,
  `user_id` INT(11) NOT NULL,
  `provider` VARCHAR(40) NOT NULL,
  `data` TEXT NOT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` VARCHAR(45) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_links_users1_idx` (`user_id` ASC),
  CONSTRAINT `fk_links_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`app_configs`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`app_configs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `app` VARCHAR(64) NOT NULL,
  `version_string` VARCHAR(64) NOT NULL DEFAULT '',
  `feature` VARCHAR(64) NULL DEFAULT NULL,
  `enabled` TINYINT(1) NOT NULL DEFAULT false,
  `current` TINYINT(1) NOT NULL DEFAULT false,
  `config` TEXT NULL DEFAULT NULL,
  `created_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `app_UNIQUE` (`app` ASC, `version_string` ASC, `feature` ASC))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`serialize`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`serialize` (
  `app` VARCHAR(64) NOT NULL,
  `object_name` VARCHAR(64) NOT NULL,
  `owner_id` VARCHAR(64) NULL,
  `expirey_date` DATETIME NOT NULL,
  `server` VARCHAR(64) NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL COMMENT '	',
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`app`, `object_name`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`email_users`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`email_users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(256) NOT NULL,
  `status` VARCHAR(45) NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media_share_messages`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media_share_messages` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NOT NULL,
  `media_share_id` INT(11) NOT NULL,
  `contact_id` INT(11) NOT NULL,
  `message` TEXT NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uuid_UNIQUE` (`uuid` ASC),
  INDEX `fk_media_share_messages_media_shares1_idx` (`media_share_id` ASC),
  INDEX `fk_media_share_messages_contacts1_idx` (`contact_id` ASC),
  CONSTRAINT `fk_media_share_messages_media_shares1`
    FOREIGN KEY (`media_share_id`)
    REFERENCES `video_dev_1`.`media_shares` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_share_messages_contacts1`
    FOREIGN KEY (`contact_id`)
    REFERENCES `video_dev_1`.`contacts` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`ui_kv_store`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`ui_kv_store` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `domain` VARCHAR(64) NOT NULL,
  `key` VARCHAR(128) NOT NULL,
  `value` TEXT NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `domain_UNIQUE` (`domain` ASC, `key` ASC))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`contact_groups`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`contact_groups` (
  `group_id` INT(11) NOT NULL,
  `contact_id` INT(11) NULL DEFAULT NULL,
  `contact_viblio_id` INT NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`group_id`, `contact_id`),
  INDEX `fk_contact_groups_contacts2_idx` (`contact_id` ASC),
  INDEX `fk_contact_groups_contacts3_idx` (`contact_viblio_id` ASC),
  CONSTRAINT `fk_contact_groups_contacts1`
    FOREIGN KEY (`group_id`)
    REFERENCES `video_dev_1`.`contacts` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_contact_groups_contacts2`
    FOREIGN KEY (`contact_id`)
    REFERENCES `video_dev_1`.`contacts` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_contact_groups_contacts3`
    FOREIGN KEY (`contact_viblio_id`)
    REFERENCES `video_dev_1`.`contacts` (`contact_viblio_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media_albums`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media_albums` (
  `album_id` INT(11) NOT NULL,
  `media_id` INT(11) NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`album_id`, `media_id`),
  INDEX `fk_media_albums_media2_idx` (`media_id` ASC),
  CONSTRAINT `fk_media_albums_media1`
    FOREIGN KEY (`album_id`)
    REFERENCES `video_dev_1`.`media` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_albums_media2`
    FOREIGN KEY (`media_id`)
    REFERENCES `video_dev_1`.`media` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`workflow_stages`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`workflow_stages` (
  `stage` VARCHAR(64) NOT NULL,
  `created_date` DATETIME NULL,
  `updated_date` VARCHAR(45) NULL,
  PRIMARY KEY (`stage`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`media_workflow_stages`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`media_workflow_stages` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `media_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `workflow_stage` VARCHAR(64) NOT NULL,
  `created_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_media_workflow_stages_media1_idx` (`media_id` ASC, `user_id` ASC),
  INDEX `fk_media_workflow_stages_workflow_stages1_idx` (`workflow_stage` ASC),
  CONSTRAINT `fk_media_workflow_stages_media1`
    FOREIGN KEY (`media_id` , `user_id`)
    REFERENCES `video_dev_1`.`media` (`id` , `user_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_workflow_stages_workflow_stages1`
    FOREIGN KEY (`workflow_stage`)
    REFERENCES `video_dev_1`.`workflow_stages` (`stage`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`organization_users`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`organization_users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `organization_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `organization_uid` VARCHAR(128) NULL,
  `created_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  PRIMARY KEY (`id`, `organization_id`, `user_id`),
  INDEX `fk_organization_users_users1_idx` (`organization_id` ASC),
  INDEX `fk_organization_users_users2_idx` (`user_id` ASC),
  CONSTRAINT `fk_organization_users_users1`
    FOREIGN KEY (`organization_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_organization_users_users2`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`communities`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`communities` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `uuid` VARCHAR(36) NOT NULL,
  `name` VARCHAR(128) NULL DEFAULT NULL,
  `webhook` TEXT NULL DEFAULT NULL,
  `members_id` INT(11) NULL DEFAULT NULL,
  `media_id` INT(11) NULL DEFAULT NULL,
  `curators_id` INT(11) NULL DEFAULT NULL,
  `pending_id` INT(11) NULL DEFAULT NULL,
  `is_curated` TINYINT(1) NOT NULL DEFAULT true,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`, `user_id`),
  INDEX `fk_communities_users1_idx` (`user_id` ASC),
  INDEX `fk_communities_media1_idx` (`media_id` ASC),
  INDEX `fk_communities_media2_idx` (`pending_id` ASC),
  INDEX `fk_communities_contacts1_idx` (`members_id` ASC),
  INDEX `fk_communities_contacts2_idx` (`curators_id` ASC),
  CONSTRAINT `fk_communities_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_communities_media1`
    FOREIGN KEY (`media_id`)
    REFERENCES `video_dev_1`.`media` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_communities_media2`
    FOREIGN KEY (`pending_id`)
    REFERENCES `video_dev_1`.`media` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_communities_contacts1`
    FOREIGN KEY (`members_id`)
    REFERENCES `video_dev_1`.`contacts` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_communities_contacts2`
    FOREIGN KEY (`curators_id`)
    REFERENCES `video_dev_1`.`contacts` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`viblio_added_content`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`viblio_added_content` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `media_id` INT(11) NULL,
  `media_user_id` INT(11) NULL,
  `album_id` INT(11) NOT NULL,
  `album_user_id` INT(11) NOT NULL,
  `content_type` VARCHAR(32) NULL DEFAULT NULL,
  `status` VARCHAR(32) NULL DEFAULT NULL,
  `attempts` INT NULL DEFAULT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_viblio_added_content_users1_idx` (`user_id` ASC),
  INDEX `fk_viblio_added_content_media1_idx` (`media_id` ASC, `media_user_id` ASC),
  INDEX `fk_viblio_added_content_media2_idx` (`album_id` ASC, `album_user_id` ASC),
  CONSTRAINT `fk_viblio_added_content_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_viblio_added_content_media1`
    FOREIGN KEY (`media_id` , `media_user_id`)
    REFERENCES `video_dev_1`.`media` (`id` , `user_id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
  CONSTRAINT `fk_viblio_added_content_media2`
    FOREIGN KEY (`album_id` , `album_user_id`)
    REFERENCES `video_dev_1`.`media` (`id` , `user_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `video_dev_1`.`user_devices`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `video_dev_1`.`user_devices` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `network` VARCHAR(64) NOT NULL,
  `device_id` VARCHAR(1024) NOT NULL,
  `created_date` DATETIME NULL DEFAULT NULL,
  `updated_date` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  INDEX `fk_user_devices_users1_idx` (`user_id` ASC),
  CONSTRAINT `fk_user_devices_users1`
    FOREIGN KEY (`user_id`)
    REFERENCES `video_dev_1`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;

CREATE USER 'video_dev_1' IDENTIFIED BY 'video_dev_1';


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;

-- -----------------------------------------------------
-- Data for table `video_dev_1`.`providers`
-- -----------------------------------------------------
START TRANSACTION;
USE `video_dev_1`;
INSERT INTO `video_dev_1`.`providers` (`provider`, `created_date`, `updated_date`) VALUES ('facebook', NULL, NULL);
INSERT INTO `video_dev_1`.`providers` (`provider`, `created_date`, `updated_date`) VALUES ('local', NULL, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `video_dev_1`.`user_types`
-- -----------------------------------------------------
START TRANSACTION;
USE `video_dev_1`;
INSERT INTO `video_dev_1`.`user_types` (`type`, `created_date`, `updated_date`) VALUES ('individual', NULL, NULL);
INSERT INTO `video_dev_1`.`user_types` (`type`, `created_date`, `updated_date`) VALUES ('organization', NULL, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `video_dev_1`.`media_types`
-- -----------------------------------------------------
START TRANSACTION;
USE `video_dev_1`;
INSERT INTO `video_dev_1`.`media_types` (`type`, `created_date`, `updated_date`) VALUES ('original', NULL, NULL);
INSERT INTO `video_dev_1`.`media_types` (`type`, `created_date`, `updated_date`) VALUES ('fb_face', NULL, NULL);
INSERT INTO `video_dev_1`.`media_types` (`type`, `created_date`, `updated_date`) VALUES ('fb_album', NULL, NULL);
INSERT INTO `video_dev_1`.`media_types` (`type`, `created_date`, `updated_date`) VALUES ('music', NULL, NULL);
INSERT INTO `video_dev_1`.`media_types` (`type`, `created_date`, `updated_date`) VALUES ('image', NULL, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `video_dev_1`.`feature_types`
-- -----------------------------------------------------
START TRANSACTION;
USE `video_dev_1`;
INSERT INTO `video_dev_1`.`feature_types` (`type`, `created_date`, `updated_date`) VALUES ('face', NULL, NULL);
INSERT INTO `video_dev_1`.`feature_types` (`type`, `created_date`, `updated_date`) VALUES ('activity', NULL, NULL);
INSERT INTO `video_dev_1`.`feature_types` (`type`, `created_date`, `updated_date`) VALUES ('fb_face', NULL, NULL);
INSERT INTO `video_dev_1`.`feature_types` (`type`, `created_date`, `updated_date`) VALUES ('tag', NULL, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `video_dev_1`.`asset_types`
-- -----------------------------------------------------
START TRANSACTION;
USE `video_dev_1`;
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('main', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('poster', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('thumbnail', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('video', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('image', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('original', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('thumbnail_animated', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('poster_animated', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('face', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('fb_face', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('main_sd', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('poster_original', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('fb_album', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('music', NULL, NULL);
INSERT INTO `video_dev_1`.`asset_types` (`type`, `created_date`, `updated_date`) VALUES ('banner', NULL, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `video_dev_1`.`share_types`
-- -----------------------------------------------------
START TRANSACTION;
USE `video_dev_1`;
INSERT INTO `video_dev_1`.`share_types` (`type`, `created_date`, `updated_date`) VALUES ('private', NULL, NULL);
INSERT INTO `video_dev_1`.`share_types` (`type`, `created_date`, `updated_date`) VALUES ('hidden', NULL, NULL);
INSERT INTO `video_dev_1`.`share_types` (`type`, `created_date`, `updated_date`) VALUES ('public', NULL, NULL);
INSERT INTO `video_dev_1`.`share_types` (`type`, `created_date`, `updated_date`) VALUES ('potential', NULL, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `video_dev_1`.`roles`
-- -----------------------------------------------------
START TRANSACTION;
USE `video_dev_1`;
INSERT INTO `video_dev_1`.`roles` (`id`, `role`, `created_date`, `updated_date`) VALUES (1, 'admin', NULL, NULL);
INSERT INTO `video_dev_1`.`roles` (`id`, `role`, `created_date`, `updated_date`) VALUES (2, 'dbadmin', NULL, NULL);
INSERT INTO `video_dev_1`.`roles` (`id`, `role`, `created_date`, `updated_date`) VALUES (3, 'instructor', NULL, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `video_dev_1`.`workflow_stages`
-- -----------------------------------------------------
START TRANSACTION;
USE `video_dev_1`;
INSERT INTO `video_dev_1`.`workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('PopeyeComplete', NULL, NULL);
INSERT INTO `video_dev_1`.`workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('TranscodeComplete', NULL, NULL);
INSERT INTO `video_dev_1`.`workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('FaceDetectComplete', NULL, NULL);
INSERT INTO `video_dev_1`.`workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('FaceRecognizeComplete', NULL, NULL);
INSERT INTO `video_dev_1`.`workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('WorkflowComplete', NULL, NULL);
INSERT INTO `video_dev_1`.`workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('WorkflowFailed', NULL, NULL);
INSERT INTO `video_dev_1`.`workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('ActivityDetectComplete', NULL, NULL);
INSERT INTO `video_dev_1`.`workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('NotifyCompleteComplete', NULL, NULL);

COMMIT;

USE `video_dev_1`;

DELIMITER $$
USE `video_dev_1`$$



CREATE
	TRIGGER provider_created BEFORE INSERT ON providers FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER provider_updated BEFORE UPDATE ON providers FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER user_type_created BEFORE INSERT ON user_types FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER user_type_updated BEFORE UPDATE ON user_types FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_type_created BEFORE INSERT ON media_types FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_type_updated BEFORE UPDATE ON media_types FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_created BEFORE INSERT ON media FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_updated BEFORE UPDATE ON media FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER user_created BEFORE INSERT ON users FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER user_updated BEFORE UPDATE ON users FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER feature_type_created BEFORE INSERT ON feature_types FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER feature_type_updated BEFORE UPDATE ON feature_types FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER contact_created BEFORE INSERT ON contacts FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER contact_updated BEFORE UPDATE ON contacts FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER asset_type_created BEFORE INSERT ON asset_types FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER asset_type_updated BEFORE UPDATE ON asset_types FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_asset_created BEFORE INSERT ON media_assets FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_asset_updated BEFORE UPDATE ON media_assets FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_asset_feature_created BEFORE INSERT ON media_asset_features FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_asset_feature_updated BEFORE UPDATE ON media_asset_features FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_comment_created BEFORE INSERT ON media_comments FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_comment_updated BEFORE UPDATE ON media_comments FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER share_type_created BEFORE INSERT ON share_types FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER share_type_updated BEFORE UPDATE ON share_types FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_share_created BEFORE INSERT ON media_shares FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_share_updated BEFORE UPDATE ON media_shares FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER session_created BEFORE INSERT ON sessions FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER session_updated BEFORE UPDATE ON sessions FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER role_created BEFORE INSERT ON roles FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER role_updated BEFORE UPDATE ON roles FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER pending_user_created BEFORE INSERT ON pending_users FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER pending_user_updated BEFORE UPDATE ON pending_users FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER password_reset_created BEFORE INSERT ON password_resets FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER password_reset_updated BEFORE UPDATE ON password_resets FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER profile_created BEFORE INSERT ON profiles FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER profile_updated BEFORE UPDATE ON profiles FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER profile_field_created BEFORE INSERT ON profile_fields FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER profile_field_updated BEFORE UPDATE ON profile_fields FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER link_created BEFORE INSERT ON links FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER link_updated BEFORE UPDATE ON links FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER app_config_updated BEFORE UPDATE ON app_configs FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER app_config_created BEFORE INSERT ON app_configs FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER serialize_created BEFORE INSERT ON serialize FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER serialize_updated BEFORE UPDATE ON serialize FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER email_users_created BEFORE INSERT ON email_users FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER email_users_updated BEFORE UPDATE ON email_users FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_share_message_created BEFORE INSERT ON media_share_messages FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_share_message_updated BEFORE UPDATE ON media_share_messages FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER ui_kv_store_created BEFORE INSERT ON ui_kv_store FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER ui_kv_store_updated BEFORE UPDATE ON ui_kv_store FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER contact_group_created BEFORE INSERT ON contact_groups FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER contact_group_updated BEFORE UPDATE ON contact_groups FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_album_created BEFORE INSERT ON media_albums FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_album_updated BEFORE UPDATE ON media_albums FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER workflow_stage_created BEFORE INSERT ON workflow_stages FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER workflow_stage_updated BEFORE UPDATE ON workflow_stages FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_workflow_stage_created BEFORE INSERT ON media_workflow_stages FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER media_workflow_stage_updated BEFORE UPDATE ON media_workflow_stages FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER organization_user_created BEFORE INSERT ON organization_types FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER organization_user_updated BEFORE UPDATE ON organization_users FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER community_created BEFORE INSERT ON communities FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER community_updated BEFORE UPDATE ON communities FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER viblio_added_content_created BEFORE INSERT ON viblio_added_content FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER viblio_added_content_updated BEFORE UPDATE ON viblio_added_content FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER user_devices_created BEFORE INSERT ON user_devices FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

USE `video_dev_1`$$



CREATE
	TRIGGER user__devices_updated BEFORE UPDATE ON user_devices FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$


DELIMITER ;
