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

#establish pocketsphinx configuration
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
def checkFollowUp(sentence):
	print "Current Question: " + str(currentQuestion)
	global followup
	print "Follow up status pre-question: " + str(followup)

	if questionSet[currentQuestion][2] != '' and followup == False:
		followup = True
		print "there's a follow up here"
		# print questionSet[currentQuestion][2]
		speak(questionSet[currentQuestion][2])
		listen()

	elif followup == True:
		if questionSet[currentQuestion][3] == 'intro':
			followup = False
			returnQuestion("first")
						
		elif questionSet[currentQuestion][3] != 'intro':
			followup = False

	elif questionSet[currentQuestion][3] == 'intro':
		returnQuestion("first")

	elif questionCount == 6:
		returnQuestion("second")

	elif questionCount == 12:
		returnQuestion("third")

	else:
		returnQuestion(tagList)

#searching input phrase with regular expressions & emotional lexicon
def searchWords(sentence):
	tag = ''
	split = sentence.split(" ")
	if len(split) > 10:
		usedTerms = []
		numbers = []
		emotionsUsed = []

		for term in terms:
			number = 0
			search = re.findall(term, sentence)

			if len(search) > 0: #if a term was found
				
				number = len(search)
				usedTerms.append(term)
				numbers.append(number)
		
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
					# returnQuestion("elaboration")
					tag = 'elaboration'
			else:
				# returnQuestion(max_emotion)
				tag = max_emotion

		else:
			print "elaboration necessary"
			# returnQuestion("elaboration")
			tag = 'elaboration'

		# print usedTerms
		if len(numbers) > 1:
			max_term = max(numbers)
			index = numbers.index(max_term)
			print usedTerms[index]

		# returnQuestion(usedTerms[index])

	else:
		# returnQuestion("elaboration")
		tag = 'elaboration'
		print ("elaboration necessary")

	print "tag: " + tag
	return tag

#computer speaking back to you if exit condition is not met
def speak(number):
	filename = "/PATH/TO/audio files/" + str(number) + "_1.wav"
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
	p = pyaudio.PyAudio()
	 
	stream = p.open(format=FORMAT,
	            channels=CHANNELS,
	            rate=RATE,
	            input=True,
	            input_device_index=0,
	            frames_per_buffer=CHUNK)

	# stream.start_stream()
	in_speech_bf = True
	decoder.start_utt()

	global lastSavedTime, text
	lastSavedTime = time.time()
	tag = ''
	savedText = ''
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
		                # print 'Partial decoding result: ' + str(decoder.hyp().hypstr).lower()
		                # print text
		                print "Elapsed time: " + str(time.time() - lastSavedTime)

		                #process input text after every 10 seconds
		                if time.time() - lastSavedTime >= 10:

		                	#only process newest chunk of text, rather than whole thing
		                	toSplit = re.compile('%s(.*)'%savedText)
		                	m = toSplit.search(text)
		                	textChunk = m.group(1)
		                	print "text at 10 second chunk: " + textChunk

		                	#select tag for text chunk, and add it to the list of tags for this response
		                	tag = searchWords(textChunk)
		                	totalTags.append(tag)

		                	#reset saved text and time
		                	savedText = ''
		                	lastSavedTime = time.time()
		            else:
		            	print "BLANK"

		        except AttributeError:
		            pass

		        if decoder.get_in_speech():
		            # sys.stdout.write('.')
		            sys.stdout.flush()
		        if decoder.get_in_speech() != in_speech_bf:
		            in_speech_bf = decoder.get_in_speech()
		            if not in_speech_bf:
		                decoder.end_utt()
		                if text != '':

		                	#search and tag the last chunk of text
		                	toSplit = re.compile('%s(.*)'%savedText)
		                	m = toSplit.search(text)
		                	textChunk = m.group(1)
			                tag = searchWords(textChunk)
			                totalTags.append(tag)

			            	print "final text: " + text
		                print "Elapsed time: " + str(time.time() - lastSavedTime)
		                lastSavedTime = time.time()
		                print "Finishing, one moment..."
		                print totalTags
		                try:
		                    if  decoder.hyp().hypstr != '':
								final = str(decoder.hyp().hypstr).lower()
								print'Stream decoding result: ' + final

								exitCondition = re.findall("good-bye", final)

								if len(exitCondition) > 0:
									s = 'say Goodbye'
									system(s)
									sys.exit(0)

								else:
									# words = final.split(' ')
									checkFollowUp(totalTags)
									# print words
									continue
		                    else:
		                    	print "BLANK"
		                except AttributeError:
		                    pass
		                decoder.start_utt()
		                print "Listening"
		    else:
		        break

		# this is to account for buffer overflows
		except IOError as io:
			print "Buffer overflowed, please try again"

	stream.stop_stream()
	stream.close()
	p.terminate()

	print "Program ended"
	print final

#selecting a question to return to participant
#!!! REWRITE THIS to match tags in list rather than select a single tag !!!
def returnQuestion(tagList):
	selection = []
	score = 0
	chosenQuestion = ''
	doNotReuse = ["first", "second", "third", "intro"]

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

		if questionScore >= score:
			score = questionScore
			chosenQuestion = q

	# rand = randrange(0, len(selection))
	# chosen = selection[rand]

	for q in questionSet:
		for d in doNotReuse:
			if chosenQuestion[1] == q[1]:
				if q[-1] != d:
					pass
				else:
					q.append("used")
					print q
	
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

	#clear tags from previous response
	totalTags = []

	#ask highest scoring question
	print chosenQuestion[0]
	speak(chosenQuestion[1])

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
with open('files/questions.csv', 'rb') as f:
	reader = csv.reader(f, delimiter=";")
	for row in reader:
		# print len(row)
		toAdd = []
		for i in range(0, len(row)):
			toAdd.append(row[i])
		# print(toAdd)
		questionSet.append(toAdd);

print "Questions loaded!"

#introduction and first question, sets off the listening loop
returnQuestion("intro")