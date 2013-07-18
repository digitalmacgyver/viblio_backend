create user 'video_dev' identified by 'video_dev';
grant all on dev.* to 'video_dev';
revoke drop on dev.* from 'video_dev';

