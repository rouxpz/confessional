#!/usr/bin/env python

from os import system
import re, sys, time, csv, pyaudio, wave, collections, thread
from sphinxbase import *
from pocketsphinx import *
from random import randrange
from pattern.en import tenses
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

questionSet = []
currentQuestion = 0
questionCount = 0
followup = False
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

#simple word count -- NOT USED RIGHT NOW
def countWords(sentence):
	words = sentence.split(" ")
	for w in words:
		# print w

		# if the word exists already
		if w in counted:				
			print "Found a duplicate!"
			index = counted.index(w)

			#increase the count
			indices[index] += 1

		#otherwise
		else:
			#add it to both lists
			counted.append(w)
			indices.append(1)

	print counted
	print indices

#checking if there's a follow up question present
def checkFollowUp(tagList):

	orderedTags = []

	for t in tagList:
		#sorts tag list into order based on which tags were used the most
		counter = collections.Counter(t)
		if counter:
			ordered = counter.most_common()
			t = []

			#rebuild tag list based on sorted version
			for word, count in ordered:
				t.append(word)

		orderedTags.append(t)

	global followup

	#checking for follow up questions and follow up types based on database -- need to work out more detailed sorting here
	if questionSet[currentQuestion][2] != '' and followup == False:
		followup = True
		print "there's a follow up here"

		#process for hard follow up questions
		if questionSet[currentQuestion][2] == 'hard':
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			typeResponse()
			# listen()

		#process for yes/no answers; should branch in two directions
		elif questionSet[currentQuestion][2] == 'yesno':
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			typeResponse()
			# listen()

		#process for short answers; follow up only returned if the response has "short" in the tag list
		elif questionSet[currentQuestion][2] == 'short' and 'short' in tagList:
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			typeResponse()
			# listen()

		#if there's no follow up, return a question the normal way
		else:
			followup = False
			returnQuestion(orderedTags)

	#if we are currently on a follow up question:
	elif followup == True:
		#are we currently on an intro question?
		if questionSet[currentQuestion][5] == 'intro':
			followup = False
			returnQuestion([[],['warmup']])
		elif questionSet[currentQuestion][3] != 'intro':
			followup = False
			returnQuestion(orderedTags)

	#intro question with no follow up
	elif questionSet[currentQuestion][5] == 'intro':
		returnQuestion([[],['warmup']])

	#exit automatically after 30 minutes have passed
	elif elapsedTime > 1800:
		goodbye()

	#if no conditions have been met after all of that, return a question the normal way
	else:
		returnQuestion(orderedTags)

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

		for o in ordered:
			emotion, value = o
			if value == max_value:
				tags[1].append(emotion)

	if len(tags[1]) == 0:
		tags[1].append('elaboration')
		print ("elaboration necessary")

	print tags
	return tags

#computer speaking back to you if exit condition is not met
def speak(number):
	filename = "files/audio files/" + str(number) + "_1.wav"
	# filename = "files/audio files/Hello6a.wav"
	f = wave.open(filename,"rb") 

	#open pyaudio instance
	pa = pyaudio.PyAudio()

	stream = pa.open(format = pa.get_format_from_width(f.getsampwidth()),  
					channels = f.getnchannels(),  
					rate = f.getframerate(),  
					output = True)

	#read data  
	data = f.readframes(CHUNK)

	#play stream  
	while data != '':  
		stream.write(data)  
		data = f.readframes(CHUNK)

	#stop stream  
	stream.stop_stream()  
	stream.close()  

	#close pyaudio instance
	pa.terminate()


#computer listening to what you say -- keyboard entry version for testing
def typeResponse():
	totalTags = []

	say = raw_input("Text entry here: ")

	#begin text processing
	say = say.lower() #convert everything to lowercase to avoid duplicates

	exitCondition = re.findall("goodbye", say)

	if len(exitCondition) > 0:
		s = 'say Goodbye'
		system(s)
		sys.exit(0)

	else:
		newTags = searchWords(say)
		for t in newTags:
			totalTags.append(t)

		split = say.split(" ")
		if len(split) < 5:
			totalTags[1].append('short')

		print totalTags

		checkFollowUp(totalTags)

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
					decoder.end_utt()
					print "Closing OSC"
					client.close()
					break

		# this is to account for buffer overflows
		except IOError as io:
			print io
			buf = '\x00'*1024
		
		# print "garbage: " + str(gc.garbage)

	stream.stop_stream()
	stream.close()
	p.terminate()

	checkFollowUp(totalTags)

def assignTerms(sentence):

	#assigning tags based on terms in corpus
	localTags = []
	specificTags = []
	termTags = []

	words = sentence.split(" ")
	print words
	for w in words:

		for q in questionSet:
			if len(q) > 13:
				for i in range(13, len(q)):
					if w == q[i]:
						specificTags.append(w)

		for t in termCatalog:
			if w == t[0]:
				termTags.append(t[1])

	localTags.append(specificTags)
	localTags.append(termTags)

	print localTags
	return localTags

def getKey(item):
	return item[1]

#selecting a question to return to participant
def returnQuestion(tagList):
	print "returning a question!"
	print tagList
	selection = []
	narrowed = []
	final = []
	score = 0
	chosenQuestion = ''

	if len(tagList[0]) > 0:
		for word in tagList[0]:
			print word

			for q in questionSet:
				if q[len(q) - 1] != "used":
					if len(q) > 13:
						for i in range (13, len(q)):
							if word == q[i]:
								if len(selection) == 0:
									print "Adding " + q[1] + " for the first time!"
									selection.append([q, 0])
								else:
									for s in selection:
										if s[0][0] == q[0]:
											print q[1] + "is already there!"
											s[1] += 1
											break
										else:
											print "Adding " + q[1] + " to the choices!"
											selection.append([q, 0])

	if len(selection) > 0:
		for s in selection:
			print s[0][0] + " used " + str(s[1]) + " times"

		ordered = sorted(selection, key=getKey, reverse = True)

		for o in ordered:
			if o[1] == ordered[0][1]:
				print "Highest score: " + o[0][0]
				narrowed.append(o[0])

	if len(narrowed) == 1:
		print narrowed
		final.append(narrowed[0])
	elif len(narrowed) > 1:
		print "Choosing from tags"
		# go through tags to find matches
		for t in tagList[1]:
			# print t
			for n in narrowed:
				# print n
				for i in range(5, 13):
					if n[i] == t:
						print n[0]
						final.append(n)
	elif len(narrowed) == 0:
		print "Choosing from tags"
		# go through tags to find matches
		for t in tagList[1]:
			# print t
			for q in questionSet:
				if q[len(q)-1] != "used":
					for i in range(5, 13):
						if q[i] == t:
							print q[0]
							final.append(q)

	if len(final) > 1:
		rand = randrange(0, len(final))
		print "index chosen: " + str(rand)
		chosenQuestion = final[rand]
		print chosenQuestion
	elif len(final) == 1:
		chosenQuestion = final[0]
		print chosenQuestion
	else:
		print "elaboration needed"

	for q in questionSet:
		if chosenQuestion[1] == q[1]:
			print q[1] + " has been used"
			q.append("used")
			print q
	
	# modify current question variable to eventually see if there's a tied in follow up
	global currentQuestion
	currentQuestion = questionSet.index(chosenQuestion)
	print "Current Question: " + str(currentQuestion)

	global questionCount
	questionCount += 1
	print questionCount

	global lastSavedTime
	print "Elapsed time: " + str(time.time() - lastSavedTime)
	lastSavedTime = time.time()

	# #ask highest scoring question
	print chosenQuestion[0]

	# #write list of tags used & resulting question to transcript
	with open(savedFile, "a") as toSave:
		toSave.write('\n\n')
		toSave.write('Tags found: ' + str(tagList) + '\n')
		toSave.write('Question chosen: ' + chosenQuestion[0] + '\n')

	try:
		speak(chosenQuestion[1])
	except IOError:
		pass

	#clear out question selection list for next response
	# selection = []
	global elapsedTime
	elapsedTime = time.time() - startingTime
	print "Time since beginning of program: " + str(elapsedTime) + " seconds"

	#call listen() again to keep the program going until exit
	typeResponse()
	# listen()

def waitingPeriod():

	#waits for indication to start -- key press for now, will likely be replaced by a sensor
	global startingTime
	global savedFile

	start = int(raw_input('>'))

	if start == 0:
		startingTime = time.time()
		savedFile = "transcript" + str(startingTime) + ".txt"
		print "Program starting"
		returnQuestion([[],['intro']])
	else:
		print "Sorry, wrong key"

		waitingPeriod()

#if 30 min have passed, go back to waiting period
def goodbye():
	speak("bye")

	for q in questionSet:
		for i in range(0, len(q)):

			#clearing out "used" tags for the next participant
			if q[i] == "used":
				q.remove(q[i])

	waitingPeriod()


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

#load questions
with open('files/questions.csv', 'rU') as f:
	reader = csv.reader(f, delimiter=";")
	for row in reader:
		toAdd = []
		for i in range(0, len(row)):
			toAdd.append(row[i])
		questionSet.append(toAdd);

print "Questions loaded!"

#starts program by waiting for indication that we're ready to go
waitingPeriod()