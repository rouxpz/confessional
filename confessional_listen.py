from os import system
import re, sys, time, csv, pyaudio, wave, collections
from sphinxbase import *
from pocketsphinx import *
from random import randrange
from pattern.en import tenses
import OSC, threading
from OSC import OSCClient, OSCMessage

#TODO 7/1/15
#1 - separate threads audio out vs. audio in
#2 - code follow up paths for short/long answers, dig deeper answers, yes/no answers
#3 - ending flow questions

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
config.set_int('-vad_postspeech', 100)

decoder = Decoder(config)

#initialize e'rrythang
counted = []
indices = []

lastSavedTime = time.time()
text = ''
savedFile = ''

#global list to hold the total tags for each response
totalTags = []

#terms to select question
terms = ["belief", "childhood", "crazy", "family", "hurt", "love", "money", "secret", "sex", "trust", "work", "worry", "wrong"]
termCatalog = []

#empty list to store emotional content
emotions = []

#waiting period to open the program
def waitingPeriod():

	#waits for indication to start -- key press for now, will likely be replaced by a sensor
	global startingTime
	global savedFile

	start = int(raw_input('>'))

	if start == 0:
		print "Opening OSC"
		client = OSCClient()
		client.connect( ("localhost", 9000) )
		startingTime = time.time()
		savedFile = "transcript" + str(startingTime) + ".txt"
		print "Program starting"
		# returnQuestion(['intro'])
		msg = OSCMessage()
		msg.setAddress("/print")
		msg.append('intro')
		client.send(msg)
		print "Closing OSC"
		client.close()

	else:
		print "Sorry, wrong key"
		waitingPeriod()

#searching input phrase with regular expressions & emotional lexicon
def searchWords(sentence):
	tags = []
	split = sentence.split(" ")
	numbers = []
	emotionsUsed = []

	for s in split:
		print tenses(s)

	# collect thematic tags from text analysis
	localTags = assignTerms(sentence)
	print localTags
	for t in localTags:
		tags.append(t)
	
	#collect emotion tags
	for emotion in emotions:
		er = r"\s" + emotion[0] + r"\s"
		emotion_match = re.search(er, sentence)
		if emotion_match != None:
			if len(emotion) < 10:
				for i in range(1, len(emotion)):
					print emotion[0] + ", " + emotion[i]
					emotionsUsed.append(emotion[i])

	#which emotion is used most; need to change this to weight more accurately, right now if two emotions are equal an elaboration is returned
	counter = collections.Counter(emotionsUsed)
	print counter
	if counter:
		ordered = counter.most_common()
		print ordered
		max_emotion, max_value = ordered[0]

		if len(ordered) > 1:
			second_emotion, second_value = ordered[1]
			# print max_emotion + ", " + second_emotion
			if max_value > second_value:
				# returnQuestion(max_emotion)
				tag = max_emotion
			else:
				print "elaboration necessary"
				tags.append('elaboration')
		else:
			tags.append(max_emotion)

	if len(tags) == 0:
		tags.append('elaboration')
		print ("elaboration necessary")

	print tags
	return tags

#computer listening to what you say
def listen():

	print "Opening OSC"
	client = OSCClient()
	client.connect( ("localhost", 9000) )

	totalTags = []
	print totalTags

	text = ''

	p = pyaudio.PyAudio()
	totalTime = 0;
	
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

						#process input text after every 10 seconds
						if time.time() - lastSavedTime >= 10:
							totalTime += time.time() - lastSavedTime

							#only process newest chunk of text, rather than whole thing
							toSplit = re.compile('%s(.*)'%savedText)
							m = toSplit.search(text)
							textChunk = m.group(1)
							print "text at 10 second chunk: " + textChunk

							#select tags for text chunk, and add them to the list of tags for this response
							newTags = searchWords(textChunk)
							for t in newTags:
								totalTags.append(t)

							#reset saved text and time
							savedText = text
							print "saved text: " + savedText
							lastSavedTime = time.time()

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

				elif silence > 120:
					#finishing up the response
					if text != '':

						# print "Elapsed time: " + str(time.time() - lastSavedTime)
						totalTime += time.time() - lastSavedTime
						print "total time: " + str(totalTime)

						if totalTime < 10:
							totalTags.append('short')

						#search and tag the last chunk of text
						toSplit = re.compile('%s(.*)'%savedText)
						m = toSplit.search(text)
						if m != None:
							textChunk = m.group(1)
							newTags = searchWords(textChunk)
						else:
							newTags = searchWords(text)
							
						for t in newTags:
							# if t not in totalTags:
							totalTags.append(t)

						print "final text: " + text
						with open(savedFile, "a") as toSave:
							toSave.write('Response: ' + text)
							toSave.write('\n')
					decoder.end_utt()
					break

				elif decoder.get_in_speech() == False and passedTime > 5:
					#finishing up the response
					if text != '':

						# print "Elapsed time: " + str(time.time() - lastSavedTime)
						totalTime += time.time() - lastSavedTime
						print "total time: " + str(totalTime)

						if totalTime < 10:
							totalTags.append('short')

						#search and tag the last chunk of text
						toSplit = re.compile('%s(.*)'%savedText)
						m = toSplit.search(text)
						if m != None:
							textChunk = m.group(1)
							newTags = searchWords(textChunk)
						else:
							newTags = searchWords(text)
							
						for t in newTags:
							# if t not in totalTags:
							totalTags.append(t)

						print "final text: " + text
						with open(savedFile, "a") as toSave:
							toSave.write('Response: ' + text)
							toSave.write('\n')

					print "checking follow up"
					msg = OSCMessage()
					msg.setAddress("/print")
					msg.append(totalTags)
					client.send(msg)
					client.close()
					print "Closed OSC"
					break

		# this is to account for buffer overflows
		except IOError as io:
			print io
			buf = '\x00'*1024
		
		# print "garbage: " + str(gc.garbage)

	decoder.end_utt()
	stream.stop_stream()
	stream.close()
	p.terminate()

	print "TERMINATED"

	# checkFollowUp(totalTags)

def assignTerms(sentence):

	#assigning tags based on terms in corpus
	localTags = []
	words = sentence.split(" ")
	print words
	for w in words:
		for t in termCatalog:
			if w == t[0]:
				localTags.append(t[1])
	return localTags
	# print localTags

# define a message-handler function for the server to call.
def receive_text(addr, tags, stuff, source):
    print "---"
    print "received new osc msg from %s" % OSC.getUrlStr(source)
    print "with addr : %s" % addr
    print "typetags %s" % tags
    print "data %s" % stuff
    print "---"
    listen()

##### MAIN SCRIPT #####

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