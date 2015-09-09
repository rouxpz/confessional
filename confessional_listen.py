from os import system
import re, sys, time, csv, pyaudio, wave, collections
from sphinxbase import *
from pocketsphinx import *
from random import randrange
from pattern.en import tenses
import OSC, threading
from OSC import OSCClient, OSCMessage

#TODO 9/7/15
#1 - confidence score for pocketsphinx (?)
#2 - pattern integration for grammatical purposes (?)
#3 - machine learning to add words to corpus
#4 - add emotional content back in

#define pocketsphinx language and acoustic models
lm = 'files/en-70k-0.1.lm'
hmm = 'files/cmusphinx-en-us-5.2'
dic = 'files/cmudict-master/cmudict_SPHINX_40.dict'

#define pyaudio input mic specs
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

s = OSC.OSCServer( ("localhost", 8001) )
s.addDefaultHandlers()

# establish pocketsphinx configuration
config = Decoder.default_config()
config.set_string('-lm', lm)
config.set_string('-hmm', hmm)
config.set_string('-dict', dic)
config.set_float('-vad_threshold',2.0)
config.set_int('-vad_postspeech', 200)

decoder = Decoder(config)

#initialize e'rrythang
counted = []
indices = []
questionSet = []

lastSavedTime = time.time()
text = ''
savedFile = ''
toAnswer = ''
pauseLength = 0

#global list to hold the total tags for each response
totalTags = []
sessionTime = 0
savedSessionTime = 0

#terms to select question
terms = ["belief", "childhood", "hurt", "love", "secret", "sex", "worry", "wrong", "yes", "skipwarmup"]
termCatalog = []

#empty list to store emotional content
emotions = []

#waiting period to open the program
def waitingPeriod():

	#waits for indication to start -- key press for now, will likely be replaced by a sensor
	global sessionTime
	global savedSessionTime
	global savedFile

	start = int(raw_input('>'))

	if start == 0:
		print "Opening OSC"
		client = OSCClient()
		client.connect( ("localhost", 9000) )
		sessionTime = 0
		print "new session time: " + str(sessionTime)
		savedSessionTime = time.time()
		savedFile = "transcript" + str(savedSessionTime) + ".txt"

		print "Program starting"
		# returnQuestion(['intro'])
		msg = OSCMessage()
		msg.setAddress("/print")
		msg.append('*')
		msg.append('intro')
		msg.append(savedFile)
		client.send(msg)
		print "Closing OSC"
		client.close()
		return

	else:
		print "Sorry, wrong key"
		waitingPeriod()

#searching input phrase with regular expressions & emotional lexicon
def searchWords(sentence):
	tags = []
	split = sentence.split(" ")
	numbers = []
	emotionsUsed = []

	# for s in split:
	# 	print tenses(s)

	# collect thematic tags from text analysis
	localTags = assignTerms(sentence)
	print localTags
	for t in localTags:
		tags.append(t)
	
	#collect emotion tags
	# for emotion in emotions:
	# 	er = r"\s" + emotion[0] + r"\s"
	# 	emotion_match = re.search(er, sentence)
	# 	if emotion_match != None:
	# 		if len(emotion) < 10:
	# 			for i in range(1, len(emotion)):
	# 				print emotion[0] + ", " + emotion[i]
	# 				emotionsUsed.append(emotion[i])

	#which emotion is used most; need to change this to weight more accurately, right now if two emotions are equal an elaboration is returned
	# counter = collections.Counter(emotionsUsed)
	# print counter
	# if counter:
	# 	ordered = counter.most_common()
	# 	print ordered
	# 	max_emotion, max_value = ordered[0]

	# 	for o in ordered:
	# 		emotion, value = o
	# 		if value == max_value:
	# 			tags[1].append(emotion)

	# if len(tags[1]) == 0:
	# 	tags[1].append('current')
	# 	print ("elaboration necessary")

	# print tags
	return tags

#computer listening to what you say
def listen():

	global sessionTime, toAnswer, pauseLength
	print "question to answer: " + toAnswer

	for q in questionSet:
		if toAnswer in q:
			# print q
			if 'intro' in q:
				if 'Hello5a' not in q:
					pauseLength = 2
				else:
					pauseLength = 10
			elif 'warmup' in q:
				pauseLength = 3
			elif 'gettingwarmer' in q:
				pauseLength = 3
			else:
				pauseLength = 4

	# print "pause length: " + str(pauseLength)
	toAnswerLower = toAnswer.replace('...', ' ').replace('.', '').replace('?', '').replace('!', '').lower()
	print toAnswerLower
	# questionWords = toAnswerLower.split(' ')
	# print questionWords

	print "Opening OSC"
	client = OSCClient()
	client.connect( ("localhost", 9000) )

	totalTags = [[], []]
	print totalTags

	text = ''

	p = pyaudio.PyAudio()
	
	#open pyaudio stream
	stream = p.open(format=FORMAT,
				channels=CHANNELS,
				rate=RATE,
				input=True,
				input_device_index=0,
				frames_per_buffer=1024)

	stream.start_stream()
	in_speech_bf = True
	decoder.start_utt()

	#initialize e'rrythang
	global lastSavedTime, text
	lastSavedTime = time.time()
	tag = ''
	savedText = ''
	paused = ''
	silence = 0
	counter = 0

	#start listening
	print "Listening"

	while True:

		passedTime = time.time() - lastSavedTime

		try:
			buf = stream.read(CHUNK)
			# print buf
			if buf:
				decoder.process_raw(buf, False, False)
				counter = 0
				try:
					if  decoder.hyp().hypstr != '':
						text = str(decoder.hyp().hypstr).lower()
						# passedTime = time.time() - lastSavedTime
						print "Elapsed time: " + str(passedTime)
						# print text

						#looking for "silences" where there's no new speech coming in
						if paused == text:
							print paused
							silence += 1
						else:
							silence = 0

						paused = text

					else:
						print "BLANK"

				except AttributeError:
					pass

				if decoder.get_in_speech():
					sys.stdout.write('.')
					sys.stdout.flush()
					print decoder.get_in_speech()

				elif decoder.get_in_speech() == False and passedTime > pauseLength:

					#finishing up the response
					if text != '':

						searchText = text + ' ' + toAnswerLower
						print "text to search: " + searchText

						print "Total elapsed time: " + str(passedTime)

						newTags = searchWords(searchText)
						print len(newTags)	

						for t in newTags[0]:
							if t != '':
								totalTags[0].append(t)

						for t in newTags[1]:
							if t != '':
								totalTags[1].append(t)

						#appending appropriate time passed tags
						if passedTime < 10:
							totalTags[1].append('short')
							totalTags[1].append('current')
						elif passedTime > 200:
							totalTags[1].append('staller')


						if len(totalTags[1]) == 0:
							totalTags[1].append('current')

						print "tags collected: " + str(totalTags)

						print "final text: " + text
						with open(savedFile, "a") as toSave:
							toSave.write('Response: ' + text)
							toSave.write('\n')

					print "checking follow up"

					msg = OSCMessage()
					msg.setAddress("/print")
					if sessionTime <= 1800: #if we've still got time
						msg.append(totalTags[0])
						msg.append('*')
						msg.append(totalTags[1])
						print "message to send: " + str(msg)
					else: #otherwise, if we've gone for half an hour
						msg.append('')
						msg.append('*')
						msg.append('end')
					client.send(msg)
					client.close()
					print "Closed OSC"
					break

		# this is to account for buffer overflows
		except IOError as io:
			print io
			buf = '\x00'*1024
			passedTime = 0

	decoder.end_utt()
	stream.stop_stream()
	stream.close()
	p.terminate()

	print "TERMINATED"

def assignTerms(sentence):

	global toAnswer
	#assigning tags based on terms in corpus
	localTags = []
	specificTags = []
	termTags = []

	for q in questionSet:
		if len(q) > 8:
			for i in range(8, len(q)):
				toSearch = r'\b' + re.escape(q[i]) + r'\b'
				w = re.search(toSearch, sentence)
				if w != None:
					specificTags.append(q[i])

	for t in termCatalog:
		toSearch = r'\b' + re.escape(t[0]) + r'\b'
		w = re.search(toSearch, sentence)
		if w != None:
			if t[1] == 'skipwarmup':
				for q in questionSet:
					if toAnswer in q and 'intro' in q:
						termTags.append(t[1])
			else:
				print t[1] + " found, using " + t[0]
				termTags.append(t[1])
			


	localTags.append(specificTags)
	localTags.append(termTags)

	# print localTags
	return localTags

# define a message-handler function for the server to call.
def receive_text(addr, tags, stuff, source):

	global sessionTime, savedSessionTime, toAnswer

	print "---"
	print "received new osc msg from %s" % OSC.getUrlStr(source)
	print "with addr : %s" % addr
	print "typetags %s" % tags
	print "data %s" % stuff
	print "---"

	if "Listen now" in stuff:
		toAnswer = stuff[1]
		interval = time.time() - savedSessionTime
		sessionTime += interval
		savedSessionTime = time.time()
		print "total session time: " + str(sessionTime)
		listen()
	else:
		waitingPeriod()

##### MAIN SCRIPT #####
#load questions
with open('files/questions.csv', 'rU') as f:
	reader = csv.reader(f, delimiter=",")
	for row in reader:
		toAdd = []
		for i in range(0, len(row)):
			toAdd.append(row[i])
		questionSet.append(toAdd);

print "Questions loaded!"
# print questionSet

#load emotion lexicon
with open('files/NRC-emotion-lexicon-wordlevel-alphabetized-v0.92.csv', 'rb') as f:
	reader = csv.reader(f, delimiter=";")
	for row in reader:
		if row[2] == "1":
			if len(emotions) == 0:
				emotions.append([row[0], row[1]])
			else:
				for i in range(len(emotions)-1, len(emotions)):
					if row[0] in emotions[i]:
						emotions[i].append(row[1])
						continue
					else:
						emotions.append([row[0], row[1]])

print "Emotions loaded!"

#load term files
for term in terms:
	filename = term + ".txt"
	with open('files/' + filename, 'rb') as f:
		lines = f.read().splitlines()
		for line in lines:
			termCatalog.append([line, term])

# print termCatalog
print "Terms sorted!"

s.addMsgHandler("/print", receive_text) # adding our function

waitingPeriod()

s.addMsgHandler("/print", receive_text) # adding our function
print "\nStarting OSCServer. Use ctrl-C to quit."
st = threading.Thread(target = s.serve_forever)
st.start()

try :
    while 1 :
        time.sleep(5)

except KeyboardInterrupt :
    print "\nClosing OSCServer."
    s.close()
    print "Waiting for Server-thread to finish"
    st.join() ##!!!
    print "Done"