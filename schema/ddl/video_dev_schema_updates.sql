alter table video add uuid varchar(40);
alter table video add user_id varchar(40);
alter table video add mimetype varchar( 40);
alter table video add size int(11) not null default 0;
alter table video add uri text;