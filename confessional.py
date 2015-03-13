from os import system
import re
import sys
import speech_recognition as sr

r = sr.Recognizer()
r.pause_threshold = 0.5

counted = []
indices = []

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

	#temp terms using to test
	terms = ["government", "nation", "people", "war", "monument"]

	for term in terms:
		search = re.findall(term, sentence)

		if len(search) > 0: #if a term was found
			print term + " was used " + str(len(search)) + " times"

		else: #otherwise
			print "No match for " + term

#computer speaking back to you if exit condition is not met
def speak(sentence):
	s = 'say You said' + sentence
	system(s)
	listen() #call listen() again to keep the program going until exit

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

		# countWords(say)
		searchWords(say)

		exitCondition = re.findall("goodbye", say)

		if len(exitCondition) > 0:
			s = 'say Goodbye'
			system(s)
			sys.exit(0)

		else:
			speak(say)

	except LookupError:
		#if the computer can't understand what was said
		print("Could not understand audio")

listen()