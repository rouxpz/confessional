from os import system
import re
import sys
from sphinxbase import *
from pocketsphinx import *
import speech_recognition as sr
import csv
import pyaudio
import wave
from random import randrange
import collections

r = sr.Recognizer()
r.pause_threshold = 0.8

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

decoder = Decoder(config)

counted = []
indices = []

questionSet = []

#terms to select question
terms = ["tech", "fame", "money", "wish", "accomplish", "past", "future", "secret", "death", "identity", "lifestyle", "career", "world", "change", "passion", "opinion", "fear", "anger", "happy", "sad", "regret", "love", "sex", "family", "friends", "ethics", "meta", "elaboration"]

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

#searching input phrase with regular expressions & emotional lexicon
def searchWords(sentence):

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
			for s in split:
				if emotion[0] == s:

					for i in range(1, len(emotion)):
						print emotion[0] + ", " + emotion[i]
						emotionsUsed.append(emotion[i])

		# print emotionsUsed
		counter = collections.Counter(emotionsUsed)
		if counter:
			max_emotion = max(counter.values())
			for key, value in counter.items():
				if value == max_emotion:
					print key
		else:
			returnQuestion("elaboration")

		# print usedTerms
		if len(numbers) > 1:
			max_term = max(numbers)
			index = numbers.index(max_term)
			print usedTerms[index]

		returnQuestion("love")

	else:

		returnQuestion("elaboration")
		# print ("elaboration necessary")

#computer speaking back to you if exit condition is not met
def speak(number):
	filename = "/PATH/TO/audio files/" + str(number) + ".wav"
	f = wave.open(filename,"rb") 

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

	#close PyAudio  
	pa.terminate()

#computer listening to what you say -- pocketsphinx version
def listen():
	p = pyaudio.PyAudio()
	 
	stream = p.open(format=FORMAT,
	            channels=CHANNELS,
	            rate=RATE,
	            input=True,
	            frames_per_buffer=CHUNK)

	# stream.start_stream()
	in_speech_bf = True
	decoder.start_utt()
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
		                print 'Partial decoding result: ' + str(decoder.hyp().hypstr).lower()
		            else:
		            	print "BLANK"
		        except AttributeError:
		            pass
		        if decoder.get_in_speech():
		            sys.stdout.write('.')
		            sys.stdout.flush()
		        if decoder.get_in_speech() != in_speech_bf:
		            in_speech_bf = decoder.get_in_speech()
		            if not in_speech_bf:
		                decoder.end_utt()
		                print "Finishing, one moment..."
		                try:
		                    if  decoder.hyp().hypstr != '':
								final = str(decoder.hyp().hypstr).lower()
								print'Stream decoding result: ' + final
								exitCondition = re.findall("goodbye", final)

								if len(exitCondition) > 0:
									s = 'say Goodbye'
									system(s)
									sys.exit(0)

								else:
									words = final.split(' ')
									searchWords(final)
									print words
									break
		                    else:
		                    	print "BLANK"
		                except AttributeError:
		                    pass
		                decoder.start_utt()
		                print "Listening"
		    else:
		        break

		except IOError as io:
			print "Buffer overflowed, please try again"

	stream.stop_stream()
	stream.close()
	p.terminate()

	print "Program ended"
	print final

#computer listening to what you say -- google API version
def listen_sr():
	#accesses the microphone and begins listening
	with sr.Microphone() as source:
		print "Microphone accessed!"
		audio = r.listen(source)

	try:
		say = r.recognize(audio)

		#begin text processing
		say = say.lower() #convert everything to lowercase to avoid duplicates

		exitCondition = re.findall("goodbye", say)

		if len(exitCondition) > 0:
			s = 'say Goodbye'
			system(s)
			sys.exit(0)

		else:
			# countWords(say)
			searchWords(say)

	except LookupError:
		#if the computer can't understand what was said
		print("Could not understand audio, try again")
		listen()

def returnQuestion(term):
	selection = []

	for q in questionSet:
		if q[len(q) - 1] != "used":
			for i in range(2, len(q)):
				if q[i] == term:
					# print q
					selection.append(q)

	rand = randrange(0, len(selection))
	chosen = selection[rand]

	for q in questionSet:
		if chosen[1] == q[1]:
			q.append("used")
	
	#choose a random question to ask for now
	speak(chosen[1])
	listen() #call listen() again to keep the program going until exit


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

#introduction and first question; returnQuestion() sets off the listening loop
speak(questionSet[0][1])
returnQuestion("intro")