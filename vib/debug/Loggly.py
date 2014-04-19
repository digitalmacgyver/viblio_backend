import os, urllib, json
from subprocess import Popen, PIPE
##################################

class Loggly:
	def __init__(self, username, password):
		self.username = username
		self.password = password
		self.n = 100
	
# Returns the result of the 'query_string' as a json object
	def query(self, user, password, from_time, size, query_string):
		search_command = 'curl -u {user}:{password} "http://viblio.loggly.com/apiv2/search?q={query_string}&from={from_time}&until=now&size={size}"'.format(user=user, password=password, query_string=urllib.quote(query_string,''), from_time=from_time, size=size)

		devnull = open('/dev/null', 'w')
		request_output = Popen(search_command, shell=True, stdout=PIPE, stderr=devnull).stdout.read()
		devnull.close()
		request_obj = json.loads(request_output)
		request_id = request_obj['rsid']['id']

		event_command = 'curl -u {user}:{password} "http://viblio.loggly.com/apiv2/events?rsid={rsid}"'.format(user=user, password=password, rsid=request_id)

		devnull = open('/dev/null', 'w')
		event_endpoint_output = Popen(event_command, shell=True, stdout=PIPE, stderr=devnull).stdout.read()
		devnull.close()
		event_endpoint_obj = json.loads(event_endpoint_output)

		return event_endpoint_obj

	
#Returns all ERROR logs from 'n' hours ago until now
# output is a JSON object (actually dict)
	def get_errors(self, n_hours):
		query_string = 'logtype:json AND json.level:ERROR AND json.activity_log.media_uuid:*'
		n_hours = '-' + str(n_hours)+'h'
		event_endpoint_obj = self.query(self.username, self.password, n_hours, self.n, query_string)
		if event_endpoint_obj['total_events'] > self.n:
			event_endpoint_obj = self.query(self.username, self.password, n_hours, event_endpoint_obj['total_events'], query_string)
		return event_endpoint_obj['events']

	
#Returns all logs of a certain `media_uuid` from 'n' hours ago until now, sorted by `timestamp`
# output is an array of JSON logs (actually array of dicts)		
	def get_messages(self, media_uuid, n_hours):
		# Making query and fetching logs
		query_string = 'json.activity_log.media_uuid:' + str(media_uuid) + ' AND logtype:json AND json.level:*'
		n_hours = '-' + str(n_hours)+'h'
		event_endpoint_obj = self.query(self.username, self.password, n_hours, self.n, query_string)
		# If there are still more logs, fetch again 	
		if event_endpoint_obj['total_events'] > self.n:
			event_endpoint_obj = self.query(self.username, self.password, n_hours, event_endpoint_obj['total_events'], query_string)
		events = sorted(event_endpoint_obj['events'], key=lambda event: event['timestamp'])
		return events


