#!/usr/bin/env python

from os import system
import re, sys, time, csv, pyaudio, wave, collections
from sphinxbase import *
from pocketsphinx import *
from random import randrange

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
config.set_float('-vad_threshold', 4.0)
config.set_int('-vad_postspeech', 100)

decoder = Decoder(config)

counted = []
indices = []

questionSet = []
currentQuestion = 0
questionCount = 0
followup = False
lastSavedTime = time.time()
text = ''

totalTags = []

#terms to select question
terms = ["tech", "fame", "money", "wish", "accomplish", "past", "future", "secret", "death", "identity", "lifestyle", "career", "world", "change", "passion", "opinion", "fear", "anger", "happy", "sad", "regret", "love", "sex", "family", "friends", "ethics", "meta", "elaboration"]

#empty list to store emotional content
emotions = []

#simple word count
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
	# print "Current Question: " + str(currentQuestion)
	global followup
	# print "Follow up status pre-question: " + str(followup)

	if questionSet[currentQuestion][2] != '' and followup == False:
		followup = True
		print "there's a follow up here"

		if questionSet[currentQuestion][2] == 'hard':
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			listen()

		elif questionSet[currentQuestion][2] == 'yesno':
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			listen()

		elif questionSet[currentQuestion][2] == 'short' and 'short' in tagList:
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			listen()

		else:
			followup = False
			returnQuestion(tagList)

	elif followup == True:
		if questionSet[currentQuestion][5] == 'intro':
			followup = False
			returnQuestion(['first'])
		elif questionSet[currentQuestion][3] != 'intro':
			followup = False

	elif questionSet[currentQuestion][5] == 'intro':
		returnQuestion(['first'])

	else:
		returnQuestion(tagList)

#searching input phrase with regular expressions & emotional lexicon
def searchWords(sentence):
	tags = []
	split = sentence.split(" ")
	usedTerms = []
	numbers = []
	emotionsUsed = []

	for term in terms:
		number = 0
		search = re.findall(term, sentence)

		if len(search) > 0: #if a term was found	
			tags.append(term)
	
	for emotion in emotions:
		er = r"\s" + emotion[0] + r"\s"
		emotion_match = re.search(er, sentence)
		if emotion_match != None:
			if len(emotion) < 10:
				for i in range(1, len(emotion)):
					print emotion[0] + ", " + emotion[i]
					emotionsUsed.append(emotion[i])

	# print emotionsUsed
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

#computer listening to what you say
def listen():
	totalTags = []
	print totalTags

	text = ''

	p = pyaudio.PyAudio()
	totalTime = 0;
	 
	stream = p.open(format=FORMAT,
				channels=CHANNELS,
				rate=RATE,
				input=True,
				input_device_index=1,
				frames_per_buffer=CHUNK)

	stream.start_stream()
	# in_speech_bf = True
	decoder.start_utt()

	global lastSavedTime, text
	lastSavedTime = time.time()
	tag = ''
	savedText = ''
	paused = ''
	silence = 0
	print "Listening"

	while True:

		try:
			buf = stream.read(CHUNK)
			# print buf
			if buf:
				decoder.process_raw(buf, False, False)
				try:
					if  decoder.hyp().hypstr != '':
						text = str(decoder.hyp().hypstr).lower()
						print "Elapsed time: " + str(time.time() - lastSavedTime)
						# print text

						#process input text after every 10 seconds
						if time.time() - lastSavedTime >= 10:
							totalTime += time.time() - lastSavedTime
							# print "total time: " + str(totalTime)

							#only process newest chunk of text, rather than whole thing
							toSplit = re.compile('%s(.*)'%savedText)
							m = toSplit.search(text)
							textChunk = m.group(1)
							print "text at 10 second chunk: " + textChunk

							#select tags for text chunk, and add them to the list of tags for this response
							newTags = searchWords(textChunk)
							for t in newTags:
								if t not in totalTags:
									totalTags.append(t)

							#reset saved text and time
							savedText = text
							print "saved text " + savedText
							lastSavedTime = time.time()

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

				if silence > 30:
					decoder.end_utt()
					break

		# this is to account for buffer overflows
		except IOError as io:
			print "Buffer overflowed, please try again"

	stream.stop_stream()
	stream.close()
	p.terminate()

	if text != '':

		# print "Elapsed time: " + str(time.time() - lastSavedTime)
		totalTime += time.time() - lastSavedTime
		print "total time: " + str(totalTime)

		if totalTime < 20:
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
			if t not in totalTags:
				totalTags.append(t)

		print "final text: " + text

	print totalTags

	print "checking follow up"
	checkFollowUp(totalTags)

#selecting a question to return to participant
def returnQuestion(tagList):
	print "returning a question!"
	print tagList
	selection = []
	score = 0
	chosenQuestion = ''

	for q in questionSet:
		#initialize score of 0
		questionScore = 0

		#go through tags in tag list to find matches
		for t in tagList:
			if q[len(q) - 1] != "used":
				for i in range(3, len(q)):
					if q[i] == t:
						# add to question score
						questionScore += 1
						print q[0] + ", " + str(questionScore)
		if score > 0:
			if questionScore > score:
				score = questionScore
				chosenQuestion = q
			elif questionScore == score:
				selection.append(q)
		else:
			score = questionScore
			chosenQuestion = q

	if len(selection) > 0:
		rand = randrange(0, len(selection))
		chosenQuestion = selection[rand]

	for q in questionSet:
		if chosenQuestion[1] == q[1]:
			print q[1] + " has been used"
			q.append("used")
	
	# modify current question to eventually see if there's a tied in follow up
	global currentQuestion
	currentQuestion = questionSet.index(chosenQuestion)
	print "Current Question: " + str(currentQuestion)

	global questionCount
	questionCount += 1
	print questionCount

	global lastSavedTime
	print "Elapsed time: " + str(time.time() - lastSavedTime)
	lastSavedTime = time.time()

	#ask highest scoring question
	# print chosenQuestion
	print chosenQuestion[0]

	try:
		speak(chosenQuestion[1])
	except IOError:
		pass

	selection = []
	# print selection

	#call listen() again to keep the program going until exit
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

#load questions
with open('files/questions.csv', 'rU') as f:
	reader = csv.reader(f, delimiter=",")
	for row in reader:
		# print len(row)
		toAdd = []
		for i in range(0, len(row)):
			toAdd.append(row[i])
		# print(toAdd)
		questionSet.append(toAdd);

print "Questions loaded!"

#introduction and first question, sets off the listening loop
returnQuestion(["intro"])