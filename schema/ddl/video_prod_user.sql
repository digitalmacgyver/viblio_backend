create user 'video_prod' identified by 'video_prod';
grant all on prod.* to 'video_prod';
revoke drop on prod.* from 'video_prod';

