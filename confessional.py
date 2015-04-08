from os import system
import re
import sys
import speech_recognition as sr
import csv
import pyaudio
import wave
from random import randrange

r = sr.Recognizer()
r.pause_threshold = 0.8

counted = []
indices = []

questionSet = []

#terms to select question
terms = ["tech", "fame", "money", "wish", "accomplish", "past", "future", "secret", "death", "identity", "lifestyle", "career", "world", "change", "passion", "opinion", "fear", "anger", "happy", "sad", "regret", "love", "sex", "family", "friends", "ethics", "meta", "elaboration"]

chunk = 1024

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

#searching input phrase with regular expressions
def searchWords(sentence):

	split = sentence.split(" ")

	#if the length of whatever is said is more than 10 words
	if len(split) > 10:
		usedTerms = []
		numbers = []

		for term in terms:
			number = 0
			search = re.findall(term, sentence)

			if len(search) > 0: #if a term was found
				
				number = len(search)
				usedTerms.append(term)
				numbers.append(number)
		
		# print usedTerms
		max_term = max(numbers)
		index = numbers.index(max_term)
		print usedTerms[index]

		returnQuestion(usedTerms[index])

	#otherwise return an elaboration question to keep them talking
	else:
		returnQuestion("elaboration")

#computer speaking back to you if exit condition is not met
def speak(number):
	filename = "/PATH/TO/audio files/" + str(number) + ".wav"
	f = wave.open(filename,"rb") 

	p = pyaudio.PyAudio()

	stream = p.open(format = p.get_format_from_width(f.getsampwidth()),  
	                channels = f.getnchannels(),  
	                rate = f.getframerate(),  
	                output = True)

	#read data  
	data = f.readframes(chunk)

	#play stream  
	while data != '':  
	    stream.write(data)  
	    data = f.readframes(chunk)

	#stop stream  
	stream.stop_stream()  
	stream.close()  

	#close PyAudio  
	p.terminate()

#computer listening to what you say
def listen():
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

#main script
with open('questions.csv', 'rb') as f:
	reader = csv.reader(f, delimiter=";")
	for row in reader:
		# print len(row)
		toAdd = []
		for i in range(0, len(row)):
			toAdd.append(row[i])
		# print(toAdd)
		questionSet.append(toAdd);

#introduction and first question
speak(questionSet[0][1])
returnQuestion("intro")

#sets off the listening loop
listen()