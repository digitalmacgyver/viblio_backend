Reliability of FaceRecognize:

FaceRecognize relies on timeouts, restarts, and unique keys to ensure
reliability.

At the highest level, FaceRecognizes workflow is:

1) Accept new task.
2) Create Mechanical Turk HIT to Merge Tracks
3) Poll Mechanical Turk until the HIT is complete
4) Create N Mechanical Turk HITs for Face Recognition
5) Poll Mechanical Turk until all N HITs are complete
6) Update RDS with data about who was recognized

Because the human interaction in steps 2 and 4 could take a long time,
this job has a long timeout in our SWF workflow (36 hours).

Because a message may get missed, or a process killed, there is a 5
minute heartbeat timeout on the Recognize job.

In the event that a job has started and times out, we use the same
unique identifiers in Mechanical Turk, and instruct Mechanical Turk to
not re-create the task if it already exists.

In this way, we should eventually complete the job.

