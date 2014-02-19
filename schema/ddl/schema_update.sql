insert into asset_types ( type ) values ( 'poster_original' );


==

drop table workorders;
drop table media_workorders;

CREATE  TABLE IF NOT EXISTS `user_types` (
  `type` VARCHAR(32) NOT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`type`) )
ENGINE = InnoDB;

-- Trigger DDL Statements
DELIMITER $$

CREATE
	TRIGGER user_type_created BEFORE INSERT ON user_types FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

CREATE
	TRIGGER user_type_updated BEFORE UPDATE ON user_types FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

DELIMITER ;

insert into user_types ( type ) values ( 'individual' );
insert into user_types ( type ) values ( 'organization' );
commit;

alter table users add column api_key varchar(128) null default null after accepted_terms;
alter table users add column metadata text null default null after api_key;
alter table users add column user_type varchar(32) not null default 'individual' after metadata;

alter table users add INDEX `fk_users_user_types1` (`user_type` ASC);
alter table users add  CONSTRAINT `fk_users_user_types1`
    FOREIGN KEY (`user_type` )
    REFERENCES `user_types` (`type`)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

update users set user_type = 'individual';
commit;


CREATE  TABLE IF NOT EXISTS `organization_users` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `organization_id` INT(11) NOT NULL ,
  `user_id` INT(11) NOT NULL ,
  `organization_uid` VARCHAR(128) NULL ,
  `created_date` DATETIME NULL ,
  `updated_date` DATETIME NULL ,
  PRIMARY KEY (`id`, `organization_id`, `user_id`) ,
  INDEX `fk_organization_users_users1` (`organization_id` ASC) ,
  INDEX `fk_organization_users_users2` (`user_id` ASC) ,
  CONSTRAINT `fk_organization_users_users1`
    FOREIGN KEY (`organization_id` )
    REFERENCES `users` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_organization_users_users2`
    FOREIGN KEY (`user_id` )
    REFERENCES `users` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;

-- Trigger DDL Statements
DELIMITER $$

CREATE
	TRIGGER organization_user_created BEFORE INSERT ON organization_types FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

CREATE
	TRIGGER organization_user_updated BEFORE UPDATE ON organization_users FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

DELIMITER ;


CREATE  TABLE IF NOT EXISTS `communities` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `user_id` INT(11) NOT NULL ,
  `uuid` VARCHAR(36) NOT NULL ,
  `name` VARCHAR(128) NULL DEFAULT NULL ,
  `webhook` TEXT NULL DEFAULT NULL ,
  `members_id` INT(11) NULL DEFAULT NULL,
  `media_id` INT(11) NULL DEFAULT NULL,
  `curators_id` INT(11) NULL DEFAULT NULL,
  `pending_id` INT(11) NULL DEFAULT NULL,
  `is_curated` TINYINT(1) NOT NULL DEFAULT true ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`id`, `user_id`) ,
  INDEX `fk_communities_users1` (`user_id` ASC) ,
  INDEX `fk_communities_media1` (`media_id` ASC) ,
  INDEX `fk_communities_media2` (`pending_id` ASC) ,
  INDEX `fk_communities_contacts1` (`members_id` ASC) ,
  INDEX `fk_communities_contacts2` (`curators_id` ASC) ,
  CONSTRAINT `fk_communities_users1`
    FOREIGN KEY (`user_id` )
    REFERENCES `users` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_communities_media1`
    FOREIGN KEY (`media_id` )
    REFERENCES `media` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_communities_media2`
    FOREIGN KEY (`pending_id` )
    REFERENCES `media` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_communities_contacts1`
    FOREIGN KEY (`members_id` )
    REFERENCES `contacts` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_communities_contacts2`
    FOREIGN KEY (`curators_id` )
    REFERENCES `contacts` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;

-- Trigger DDL Statements
DELIMITER $$

CREATE
	TRIGGER community_created BEFORE INSERT ON communities FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

CREATE
	TRIGGER community_updated BEFORE UPDATE ON communities FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

DELIMITER ;

insert into feature_types ( type ) values ( 'activity' );

CREATE  TABLE IF NOT EXISTS `workflow_stages` (
  `stage` VARCHAR(64) NOT NULL ,
  `created_date` DATETIME NULL ,
  `updated_date` VARCHAR(45) NULL ,
  PRIMARY KEY (`stage`) )
ENGINE = InnoDB;

CREATE  TABLE IF NOT EXISTS `media_workflow_stages` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `media_id` INT(11) NOT NULL ,
  `user_id` INT(11) NOT NULL ,
  `workflow_stage` VARCHAR(64) NOT NULL ,
  `created_date` DATETIME NULL ,
  `updated_date` DATETIME NULL ,
  PRIMARY KEY (`id`) ,
  INDEX `fk_media_workflow_stages_media1` (`media_id` ASC, `user_id` ASC) ,
  INDEX `fk_media_workflow_stages_workflow_stages1` (`workflow_stage` ASC) ,
  CONSTRAINT `fk_media_workflow_stages_media1`
    FOREIGN KEY (`media_id` , `user_id` )
    REFERENCES `media` (`id` , `user_id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_workflow_stages_workflow_stages1`
    FOREIGN KEY (`workflow_stage` )
    REFERENCES `workflow_stages` (`stage` )
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;

DELIMITER $$

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


DELIMITER ;

DELIMITER $$


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


DELIMITER ;


START TRANSACTION;
INSERT INTO `workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('PopeyeComplete', NULL, NULL);
INSERT INTO `workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('TranscodeComplete', NULL, NULL);
INSERT INTO `workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('FaceDetectComplete', NULL, NULL);
INSERT INTO `workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('FaceRecognizeComplete', NULL, NULL);
INSERT INTO `workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('WorkflowComplete', NULL, NULL);
INSERT INTO `workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('WorkflowFailed', NULL, NULL);
INSERT INTO `workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('ActivityDetectComplete', NULL, NULL);
INSERT INTO `workflow_stages` (`stage`, `created_date`, `updated_date`) VALUES ('NotifyCompleteComplete', NULL, NULL);

COMMIT;


update media set status = 'complete' where status = 'FaceRecognizeComplete';

update media set status = 'visible' where status in ( 'FaceDetectComplete', 'TranscodeComplete' );

update media set status = 'failed' where status is null or status in ('PopeyeComplete');

update media set status = 'failed' where status not in ( 'complete', 'visible', 'failed' );


==

alter table asset_types modify column type varchar(32);
alter table media_assets modify column asset_type varchar( 32 );

===


alter table contacts add column is_group bool null default false after user_id;
alter table media add column is_album bool null default false after media_type;
alter table media_shares add column is_group_share bool null default false after share_type;

alter table media_shares add column contact_id integer null default null after user_id;
alter table media_shares add INDEX `fk_media_shares_contacts1` (`contact_id` ASC);
alter table media_shares add  CONSTRAINT `fk_media_shares_contacts1`
    FOREIGN KEY (`contact_id` )
    REFERENCES `video_dev`.`contacts` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

alter table users modify email varchar(128) null default null;
alter table users add unique index email_UNIQUE( email );

CREATE  TABLE IF NOT EXISTS `video_dev`.`contact_groups` (
  `group_id` INT(11) NOT NULL ,
  `contact_id` INT(11) NULL DEFAULT NULL ,
  `contact_viblio_id` INT NULL DEFAULT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`group_id`, `contact_id`) ,
  INDEX `fk_contact_groups_contacts2` (`contact_id` ASC) ,
  INDEX `fk_contact_groups_contacts3` (`contact_viblio_id` ASC) ,
  CONSTRAINT `fk_contact_groups_contacts1`
    FOREIGN KEY (`group_id` )
    REFERENCES `video_dev`.`contacts` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_contact_groups_contacts2`
    FOREIGN KEY (`contact_id` )
    REFERENCES `video_dev`.`contacts` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_contact_groups_contacts3`
    FOREIGN KEY (`contact_viblio_id` )
    REFERENCES `video_dev`.`contacts` (`contact_viblio_id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


CREATE  TABLE IF NOT EXISTS `video_dev`.`media_albums` (
  `album_id` INT(11) NOT NULL ,
  `media_id` INT(11) NULL DEFAULT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`album_id`, `media_id`) ,
  INDEX `fk_media_albums_media2` (`media_id` ASC) ,
  CONSTRAINT `fk_media_albums_media1`
    FOREIGN KEY (`album_id` )
    REFERENCES `video_dev`.`media` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_albums_media2`
    FOREIGN KEY (`media_id` )
    REFERENCES `video_dev`.`media` (`id` )
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


DELIMITER $$
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


DELIMITER ;

DELIMITER $$
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


DELIMITER ;

===

alter table media_assets drop column filename;
alter table media_assets drop column format;
alter table media_assets drop column time_stamp;
alter table media_assets drop column intellivision_file_id;
alter table contacts drop column intellivision_id;

alter table media add column unique_hash VARCHAR(32) NULL DEFAULT NULL after uuid;
alter table media add unique index unique_hash_UNIQUE(unique_hash,user_id);

===

alter table media add column status VARCHAR(32) NULL DEFAULT NULL after lng;

update media set status = 'FaceRecognizeComplete' where id in ( select media_id from media_assets where asset_type = 'main' );

===

alter table media_asset_features add column track_id INTEGER NULL DEFAULT NULL after recognition_confidence;

alter table media_asset_features add column recognition_result VARCHAR(32) NULL DEFAULT NULL after track_id;

insert into share_types ( type ) values 'potential';




=====

alter table media_shares add column uuid VARCHAR(36) NOT NULL after id;

alter table media_shares add unique index uuid_UNIQUE(uuid);

CREATE  TABLE IF NOT EXISTS `video_dev`.`media_share_messages` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `uuid` VARCHAR(36) NOT NULL ,
  `media_share_id` INT(11) NOT NULL ,
  `contact_id` INT(11) NOT NULL ,
  `message` TEXT NULL DEFAULT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `uuid_UNIQUE` (`uuid` ASC) ,
  INDEX `fk_media_share_messages_media_shares1` (`media_share_id` ASC) ,
  INDEX `fk_media_share_messages_contacts1` (`contact_id` ASC) ,
  CONSTRAINT `fk_media_share_messages_media_shares1`
    FOREIGN KEY (`media_share_id` )
    REFERENCES `video_dev`.`media_shares` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_media_share_messages_contacts1`
    FOREIGN KEY (`contact_id` )
    REFERENCES `video_dev`.`contacts` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;


-- Trigger DDL Statements
DELIMITER $$

USE `video_dev`$$

CREATE
	TRIGGER media_share_message_created BEFORE INSERT ON media_share_messages FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

CREATE
	TRIGGER media_share_message_updated BEFORE UPDATE ON media_share_messages FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$

delimiter ;




============

In prod:

alter table users add column confirmed BOOLEAN after active;

alter table media_shares modify column user_id int;

alter table users drop column username;

CREATE  TABLE IF NOT EXISTS `video_dev`.`email_users` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `email` VARCHAR(256) NOT NULL ,
  `status` VARCHAR(45) NULL DEFAULT NULL ,
  `created_date` DATETIME NULL DEFAULT NULL ,
  `updated_date` DATETIME NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) )
ENGINE = InnoDB;


DELIMITER $$

USE `video_dev`$$

CREATE
	TRIGGER email_users_created BEFORE INSERT ON email_users FOR EACH ROW
BEGIN
	set NEW.created_date = NOW();
END;
$$

CREATE
	TRIGGER email_users_updated BEFORE UPDATE ON email_users FOR EACH ROW
BEGIN
	set NEW.updated_date = NOW();
END;
$$


delimiter ;


===


mysqldump -h testpub.c9azfz8yt9lz.us-west-2.rds.amazonaws.com -u admin -pitonerol video_dev_1 | mysql -h testpub.c9azfz8yt9lz.us-west-2.rds.amazonaws.com -u admin -pitonerol video_dev_2

alter table contacts add column picture_uri VARCHAR(2048) NULL DEFAULT NULL after intellivision_id;

alter table media_asset_features drop foreign key fk_media_asset_features_media_assets1;
alter table media_assets drop foreign key fk_media_assets_media1;
alter table media_workorders drop foreign key fk_media_workorders_media1;
alter table media_comments drop foreign key fk_media_comments_media1;
alter table media_shares drop foreign key fk_media_shares_media1;

alter table media modify column id INTEGER;
alter table media drop primary key;
alter table media add primary key (id, user_id);
alter table media modify column id INTEGER NOT NULL AUTO_INCREMENT;

alter table media_assets add column user_id INTEGER NULL DEFAULT NULL after media_id;
create table temp as select id, user_id from media;
update media_assets set user_id = (select user_id from temp where media_assets.media_id = temp.id);
drop table temp;
alter table media_assets modify column id INTEGER;
alter table media_assets drop primary key;
alter table media_assets add primary key (id, media_id, user_id);
alter table media_assets modify column id INTEGER NOT NULL AUTO_INCREMENT;
alter table media_assets drop index fk_media_assets_media1;
alter table media_assets add INDEX `fk_media_assets_media1` (`media_id` ASC, `user_id` ASC);
alter table media_assets add CONSTRAINT `fk_media_assets_media1`
    FOREIGN KEY (`media_id` , `user_id` )
    REFERENCES `video_dev`.`media` (`id` , `user_id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE;

alter table media_asset_features add column media_id INTEGER NULL DEFAULT NULL after media_asset_id;
alter table media_asset_features add column user_id INTEGER NULL DEFAULT NULL after media_id;
create table temp as select id, media_id, user_id from media_assets;
update media_asset_features set media_id = (select media_id from temp where media_asset_features.media_asset_id = temp.id);
update media_asset_features set user_id = (select user_id from temp where media_asset_features.media_asset_id = temp.id);
drop table temp;
alter table media_asset_features modify column id INTEGER;
alter table media_asset_features drop primary key;
alter table media_asset_features add primary key (id, media_asset_id, media_id, user_id);
alter table media_asset_features modify column id INTEGER NOT NULL AUTO_INCREMENT;
alter table media_asset_features drop index fk_media_asset_features_media_assets1;
alter table media_asset_features add INDEX `fk_media_asset_features_media_assets1` (`media_asset_id` ASC, `media_id` ASC, `user_id` ASC);
alter table media_asset_features add  CONSTRAINT `fk_media_asset_features_media_assets1`
    FOREIGN KEY (`media_asset_id` , `media_id` , `user_id` )
    REFERENCES `video_dev`.`media_assets` (`id` , `media_id` , `user_id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE;


alter table media_workorders add INDEX `fk_media_workorders_media1` (`media_id` ASC);
alter table media_workorders add CONSTRAINT `fk_media_workorders_media1`
    FOREIGN KEY (`media_id` )
    REFERENCES `video_dev`.`media` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE;

alter table media_shares drop index fk_media_shares_media1;
alter table media_shares add  INDEX `fk_media_shares_media1` (`media_id` ASC);
alter table media_shares add  CONSTRAINT `fk_media_shares_media1`
    FOREIGN KEY (`media_id` )
    REFERENCES `video_dev`.`media` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE;

alter table media_comments drop foreign key fk_media_comments_media1;
alter table media_comments drop index fk_media_comments_media1;
alter table media_comments add  INDEX `fk_media_comments_media1` (`media_id` ASC);
alter table media_comments add  CONSTRAINT `fk_media_comments_media1`
    FOREIGN KEY (`media_id` )
    REFERENCES `video_dev`.`media` (`id` )
    ON DELETE CASCADE
    ON UPDATE CASCADE;