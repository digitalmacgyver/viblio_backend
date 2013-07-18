create user 'video_prod' identified by 'video_prod';
grant all on video_prod.* to 'video_prod';
revoke drop on video_prod.* from 'video_prod';

