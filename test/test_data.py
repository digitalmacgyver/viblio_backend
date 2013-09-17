from datetime import timedelta

videos = [
    { 's3_key' : 'test_data/videos/test-01.mp4',
      'bytes' : 48511420,
      'thumbnail_bytes' : 2025,
      'poster_bytes' : 4353,
      'create_delta' : timedelta( days=1 ),
      'face_idx' : [1, 3] },
    { 's3_key' : 'test_data/videos/test-02.mp4',
      'bytes' : 31310851,
      'thumbnail_bytes' : 3457,
      'poster_bytes' : 6449,
      'create_delta' : timedelta( days=7 ),
      'face_idx' : [2] },
    { 's3_key' : 'test_data/videos/test-03.mp4',
      'bytes' : 36507035,
      'thumbnail_bytes' :5232 ,
      'poster_bytes' : 11504,
      'create_delta' : timedelta( days=15 ),
      'face_idx' : [2, 4] },
    { 's3_key' : 'test_data/videos/test-04.mp4',
      'bytes' : 35153880,
      'thumbnail_bytes' : 801,
      'poster_bytes' : 1745,
      'create_delta' : timedelta( days=30 ),
      'face_idx' : [5] },
    { 's3_key' : 'test_data/videos/test-05.mp4',
      'bytes' : 35266795,
      'thumbnail_bytes' : 1019,
      'poster_bytes' : 2249,
      'create_delta' : timedelta( days=45 ),
      'face_idx' : [0, 2] },
    { 's3_key' : 'test_data/videos/test-06.mp4',
      'bytes' : 33170372,
      'thumbnail_bytes' : 1055,
      'poster_bytes' : 2196,
      'create_delta' : timedelta( days=60 ),
      'face_idx' : [0, 6] },
    { 's3_key' : 'test_data/videos/test-07.mp4',
      'bytes' : 9021554,
      'thumbnail_bytes' : 962,
      'poster_bytes' : 2252,
      'create_delta' : timedelta( days=90 ),
      'face_idx' : [0, 2, 7] },
    { 's3_key' : 'test_data/videos/test-08.mp4',
      'bytes' : 30138037,
      'thumbnail_bytes' : 1071,
      'poster_bytes' : 2008,
      'create_delta' : timedelta( days=180 ),
      'face_idx' : [8, 9, 1, 3, 4, 5, 6, 7] },
    { 's3_key' : 'test_data/videos/test-09.mp4',
      'bytes' : 249470,
      'thumbnail_bytes' : 3508,
      'poster_bytes' : 7078,
      'create_delta' : timedelta( days=370 ),
      'face_idx' : [0, 2, 8] },
    { 's3_key' : 'test_data/videos/test-0a.mp4',
      'bytes' : 4263119,
      'thumbnail_bytes' : 5159,
      'poster_bytes' : 13650,
      'create_delta' : timedelta( days=450 ),
      'face_idx' : [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] },
    { 's3_key' : 'test_data/videos/test-0b.mp4',
      'bytes' : 130131832,
      'thumbnail_bytes' : 1068,
      'poster_bytes' : 2268,
      'create_delta' : timedelta( days=800 ),
      'face_idx' : [] },
    ]


contacts = [
    { 'name' : 'Andre the Giant',
      'email' : 'viblio.smtesting+andre@gmail.com',
      'provider' : None,
      'provider_id' : None,
      'viblio_id' : None },
    { 'name' : 'David Bowie',
      'email' : 'viblio.smtesting+david@gmail.com',
      'provider' : 'facebook',
      'provider_id' : '100006092460819',
      'viblio_id' : None },
    { 'name' : 'Walt Disney',
      'email' : 'viblio.smtesting+walt@gmail.com',
      'provider' : None,
      'provider_id' : None,
      'viblio_id' : None },
    { 'name' : 'Albert Einstein',
      'email' : 'viblio.smtesting+albert@gmail.com',
      'provider' : None,
      'provider_id' : None,
      'viblio_id' : None },
    { 'name' : 'Hedy Lamarr',
      'email' : 'viblio.smtesting+hedy@gmail.com',
      'provider' : None,
      'provider_id' : None,
      'viblio_id' : None },
    { 'name' : 'Bruce Lee',
      'email' : 'viblio.smtesting+bruce@gmail.com',
      'provider' : None,
      'provider_id' : None,
      'viblio_id' : None },
    { 'name' : 'Abraham Lincoln',
      'email' : 'viblio.smtesting+abe@gmail.com',
      'provider' : None,
      'provider_id' : None,
      'viblio_id' : None },
    { 'name' : 'Nikola Tesla',
      'email' : 'viblio.smtesting+nikola@gmail.com',
      'provider' : None,
      'provider_id' : None,
      'viblio_id' : None },
    { 'name' : 'Mark Twain',
      'email' : 'viblio.smtesting+mark@gmail.com',
      'provider' : None,
      'provider_id' : None,
      'viblio_id' : None },
    ]

faces = [
    { 'filename'    : 'face-01.jpg',
      's3_key'      : 'test_data/faces/face-01.jpg',
      'size'        : 9812,
      'width'       : 150, 
      'height'      : 150,
      'contact_idx' : None },
    { 'filename'    : 'face-02.jpg',
      's3_key'      : 'test_data/faces/face-02.jpg',
      'size'        : 6387,
      'width'       : 184, 
      'height'      : 214,
      'contact_idx' : 0 },
    { 'filename'    : 'face-03.jpg',
      's3_key'      : 'test_data/faces/face-03.jpg',
      'size'        : 6507,
      'width'       : 193, 
      'height'      : 262,
      'contact_idx' : 1 },
    { 'filename'    : 'face-04.jpg',
      's3_key'      : 'test_data/faces/face-04.jpg',
      'size'        : 6333,
      'width'       : 201, 
      'height'      : 251,
      'contact_idx' : 2 },
    { 'filename'    : 'face-05.jpg',
      's3_key'      : 'test_data/faces/face-05.jpg',
      'size'        : 9361,
      'width'       : 197,
      'height'      : 256,
      'contact_idx' : 3 },
    { 'filename'    : 'face-06.jpg',
      's3_key'      : 'test_data/faces/face-06.jpg',
      'size'        : 13069,
      'width'       : 220, 
      'height'      : 285,
      'contact_idx' : 4 },
    { 'filename'    : 'face-07.jpg',
      's3_key'      : 'test_data/faces/face-07.jpg',
      'size'        : 7494,
      'width'       : 202, 
      'height'      : 250,
      'contact_idx' : 5 },
    { 'filename'    : 'face-08.jpg',
      's3_key'      : 'test_data/faces/face-08.jpg',
      'size'        : 5511,
      'width'       : 196, 
      'height'      : 257,
      'contact_idx' : 6 },
    { 'filename'    : 'face-09.jpg',
      's3_key'      : 'test_data/faces/face-09.jpg',
      'size'        : 4051,
      'width'       : 176, 
      'height'      : 236,
      'contact_idx' : 7 },
    { 'filename'    : 'face-0a.jpg',
      's3_key'      : 'test_data/faces/face-0a.jpg',
      'size'        : 7193,
      'width'       : 187, 
      'height'      : 270,
      'contact_idx' : 8 },
    ]

