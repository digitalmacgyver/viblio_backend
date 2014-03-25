create user 'video_prod' identified by 'video_prod';
grant all on video_prod.* to 'video_prod';
revoke drop on video_prod.* from 'video_prod';

create user 'web_prod' identified by 'AVxXwDC9Y%sKaPG@';
grant select, insert, update, delete, create temporary tables, lock tables, execute, trigger on video_dev.* to 'web_prod' with max_user_connections 200;

create user 'vwf_prod' identified by 'R5j*ApW2pcF*xNsK';
grant select, insert, update, delete, create temporary tables, lock tables, execute, trigger on video_dev.* to 'vwf_prod' with max_user_connections 2000;

create user 'popeye_prod' identified by '393!zyRu@2u&gyT@';
grant select, insert, update, delete, create temporary tables, lock tables, execute, trigger on video_dev.* to 'popeye_prod' with max_user_connections 200;