create user 'video_dev_1' identified by 'video_dev_1';
grant all on video_dev_1.* to 'video_dev_1';
revoke drop on video_dev_1.* from 'video_dev_1';

create user 'web_dev' identified by 'Yn8U!2Y52Pt#5MEK';
grant select, insert, update, delete, create temporary tables, lock tables, execute, trigger on video_dev_1.* to 'web_dev' with max_user_connections 200;

create user 'vwf_dev' identified by '@zjwS3F8CDRm6Bs!';
grant select, insert, update, delete, create temporary tables, lock tables, execute, trigger on video_dev_1.* to 'vwf_dev' with max_user_connections 200;

create user 'popeye_dev' identified by '&uhq3V7peaBAhExT';
grant select, insert, update, delete, create temporary tables, lock tables, execute, trigger on video_dev_1.* to 'popeye_dev' with max_user_connections 200;


