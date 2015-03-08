from os import system
import speech_recognition as sr

r = sr.Recognizer()

#accesses the microphone and begins listening
with sr.Microphone() as source:
	print "Microphone accessed!"
	audio = r.listen(source)

try:
	say = r.recognize(audio)

	#begin text processing
	say = say.lower()
	words = say.split(" ")
	for w in words:
		print w

	say = 'say ' + 'You said ' + say
	system(say)

except LookupError:
	#if the computer can't understand what was said
	print("Could not understand audio")