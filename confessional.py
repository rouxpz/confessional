from os import system
import re
import sys
import speech_recognition as sr
import csv
from random import randrange

r = sr.Recognizer()
r.pause_threshold = 0.8

counted = []
indices = []

questionSet = [[],[],[],[],[],[],[],[],[]]

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
	terms = ["past", "wish", "family", "friends", "death"]

	for term in terms:
		search = re.findall(term, sentence)

		if len(search) > 0: #if a term was found
			# print term + " was used " + str(len(search)) + " times"
			returnQuestion(term)

#computer speaking back to you if exit condition is not met
def speak(sentence):
	s = "say " + sentence
	system(s)

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

	except LookupError:
		#if the computer can't understand what was said
		print("Could not understand audio")

def returnQuestion(term):
	choose = []
	for qs in questionSet:
		for item in qs:
			for i in range(1, len(item)):
				if term in item[i]:
					choose.append(item[0])
	
	#choose a random question to ask for now
	selected = randrange(0, len(choose))
	print str(selected) + ", " + choose[selected]
	speak(choose[selected])
	listen() #call listen() again to keep the program going until exit

with open('questions.csv', 'rb') as f:
	reader = csv.reader(f, delimiter=";")
	for row in reader:
		# print len(row)
		toAdd = []
		for i in range(1, len(row)):
			toAdd.append(row[i])
		# print(toAdd)
		questionSet[int(row[0])].append(toAdd)

# print questionSet[2]
listen()