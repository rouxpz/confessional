from os import system
import speech_recognition as sr

r = sr.Recognizer()
# r.pause_threshold = 0.2

counted = []
indices = []

#accesses the microphone and begins listening
with sr.Microphone() as source:
	print "Microphone accessed!"
	audio = r.listen(source)

try:
	say = r.recognize(audio)

	#begin text processing
	say = say.lower() #convert everything to lowercase to avoid duplicates
	words = say.split(" ")
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

except LookupError:
	#if the computer can't understand what was said
	print("Could not understand audio")

print counted
print indices