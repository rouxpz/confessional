import OSC, csv, time, threading, pyaudio, wave, sys, collections
from random import randrange
from OSC import OSCClient, OSCMessage

questionSet = []
currentQuestion = 0
currentTheme = ''
questionCount = 0
notFirst = False
text = ''
savedFile = ''

terms = ["belief", "childhood", "hurt", "love", "secret", "sex", "worry", "wrong"]
termsUnused = terms

s = OSC.OSCServer( ("localhost", 9000) )
s.addDefaultHandlers()

#load questions
with open('files/questions.csv', 'rU') as f:
	reader = csv.reader(f, delimiter=",")
	for row in reader:
		toAdd = []
		for i in range(0, len(row)):
			toAdd.append(row[i])
		questionSet.append(toAdd);

print "Questions loaded!"

#checking if there's a follow up question present
def checkFollowUp(tagList):

	orderedTags = []
	tempQuestion = 0

	global currentQuestion
	global currentTheme
	# for i in range(0, len(questionSet)):
	followUpType = questionSet[currentQuestion][2]
	# followUpType = questionSet[i][2]

	if followUpType != '':
		#check followup types here
		print followUpType
		#hard follows automatically redirect to the next question
		if followUpType == 'hardfollow':
			for j in range(0, len(questionSet)):
				if questionSet[currentQuestion][3] == questionSet[j][1]:
					print "next question: " + questionSet[j][1]
					tempQuestion = j
					speak(j)
			currentQuestion = tempQuestion

		#yes/no questions look for affirmative or negative responses and respond accordingly
		elif followUpType == 'yesno':
			# response = str(raw_input('yes no question >'))
			if 'yes' in tagList[1]: #FIX THIS, you need affirmative and negative dictionaries
				if questionSet[currentQuestion][3] != '':
					for j in range(0, len(questionSet)):
						if questionSet[currentQuestion][3] == questionSet[j][1]:
							print "next question: " + questionSet[j][1]
							tempQuestion = j
							speak(j)
					currentQuestion = tempQuestion

				else:
					returnQuestion(tagList)

			else:
				if questionSet[i][4] != '':
					for j in range(0, len(questionSet)):
						if questionSet[currentQuestion][4] == questionSet[j][1]:
							print "next question: " + questionSet[j][1]
							tempQuestion = j
							speak(j)
					currentQuestion = tempQuestion

				else:
					returnQuestion(tagList)

		#length picks question by how long user response is
		elif followUpType == 'length':
			# response = str(raw_input('length question >'))
			if 'short' in tagList[1]:
				if questionSet[currentQuestion][3] != '':
					for j in range(0, len(questionSet)):
						if questionSet[currentQuestion][3] == questionSet[j][1]:
							tempQuestion = j
							speak(j)
					currentQuestion = tempQuestion

				else:
					returnQuestion(tagList)
			else:
				if questionSet[currentQuestion][4] != '':
					for j in range(0, len(questionSet)):
						if questionSet[currentQuestion][4] == questionSet[j][1]:
							print "next question: " + questionSet[j][1]
							tempQuestion = j
							speak(j)
					currentQuestion = tempQuestion

				else:
					returnQuestion(tagList)

	#if no conditions have been met after all of that, return a question the normal way
	else:
		returnQuestion(tagList)

#computer speaking back to you if exit condition is not met
def speak(number):

	global savedFile

	with open(savedFile, "a") as toSave:
		toSave.write('\n')
		toSave.write('Question generated: ' + questionSet[number][0])
		toSave.write('\n')

	question = questionSet[number]
	filename = "files/audio files/" + str(question[1]) + ".wav"
	# filename = "files/audio files/Hello6a.wav"
	f = wave.open(filename,"rb") 

	#open pyaudio instance
	pa = pyaudio.PyAudio()

	stream = pa.open(format = pa.get_format_from_width(f.getsampwidth()),  
					channels = f.getnchannels(),  
					rate = f.getframerate(),  
					output = True)

	#read data  
	data = f.readframes(1024)

	#play stream  
	while data != '':  
		stream.write(data)  
		data = f.readframes(1024)

	#stop stream  
	stream.stop_stream()  
	stream.close()  

	#close pyaudio instance
	pa.terminate()

	print "current question: " + str(number) + " " + questionSet[number][0]

	#send data out via OSC to let the other program know to start listening
	print "Opening OSC"
	client = OSCClient()
	client.connect(("localhost", 8001))
	msg = OSCMessage()
	msg.setAddress("/print")

	if 'end' in questionSet[number] and 'followup' in questionSet[number]:
		msg.append("End now")
	else:
		msg.append("Listen now")
		msg.append(questionSet[number][0])
	
	client.send(msg)
	print "Closing OSC"
	client.close()

def getKey(item):
	return item[1]

#selecting a question to return to participant
def returnQuestion(tagList):

	global currentTheme
	print currentTheme
	print "tags collected: " + str(tagList)

	beginThemes = ['intro', 'warmup', 'gettingwarmer', 'aboutyou']

	with open(savedFile, "a") as toSave:
		toSave.write('\n')
		toSave.write('Tags collected: ' + str(tagList))
		toSave.write('\n')

	#integrate "notfirst" and "escapehatch" tags in here
	print "returning a question!"
	print tagList
	selection = []
	narrowed = []
	final = []
	score = 0
	chosenQuestion = ''

	if len(tagList[0]) > 0:
		for word in tagList[0]:
			if word != '':
				print word

				for q in questionSet:
					if q[len(q) - 1] != "used":
						if len(q) > 8 and q[6] != 'followup':
							for i in range (8, len(q)):
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
	# else:
	# 	tagList[1].append(currentTheme)
	# 	return

	if len(narrowed) == 1:
		print narrowed
		final.append(narrowed[0])
	elif len(narrowed) > 1:
		if len(tagList[1]) > 0:
			print "Choosing from tags"
			# print narrowed
			# go through tags to find matches
			for t in tagList[1]:
				# print t
				for n in narrowed:
					# print n
					# if 'followup' not in n:
					if t in n:
						final.append(n)

	elif len(narrowed) == 0:
		if len(tagList[1]) > 0:
			print "Choosing from tags"
			# go through tags to find matches
			for t in tagList[1]:
				# print t
				for q in questionSet:
					if q[len(q)-1] != "used" and 'followup' not in q:

						if t in q:
							print q[0]
							final.append(q)

	# print final

	if len(final) < 1 and len(narrowed) > 1:
		# print "elaboration needed"
		rand = randrange(0, len(narrowed))
		print "index chosen: " + str(rand)
		chosenQuestion = narrowed[rand]
	elif len(final) < 1:
		if questionSet[currentQuestion][5] == 'intro':
			returnQuestion([[], ['warmup']])
			return
		elif questionSet[currentQuestion][5] == 'warmup':
			returnQuestion([[], ['gettingwarmer']])
			return
		elif questionSet[currentQuestion][5] == 'gettingwarmer':
			returnQuestion([[], ['aboutyou']])
			return
		else:
			#replacing all "current" indicators with the current theme
			indices = [i for i, x in enumerate(tagList[1]) if x == "current"]

			if currentTheme not in beginThemes:
				for i in indices:
					tagList[1][i] = currentTheme
				print "new tag list: " + str(tagList)

			else:
				randTheme = randrange(0, len(terms))
				currentTheme = terms[randTheme]

				print "new theme: " + currentTheme

				for i in indices:
					tagList[1][i] = currentTheme
				print "new tag list: " + str(tagList)

			#if nothing is found from terms, continue on current theme tag until no more questions remain, then shift to new theme with "escapehatch"
			themeUnused = []
			for q in questionSet:
				if q[len(q) - 1] != 'used' and currentTheme in q:
					themeUnused.append(q)
			if len(themeUnused) > 0:
				returnQuestion([[], [currentTheme]])
				return
			else:
				escapeQuestions = []
				for t in termsUnused:
					if t == currentTheme:
						termsUnused.remove(t)
				randIndex = randrange(0, len(termsUnused))
				newTerm = terms[randIndex]
				
				for q in questionSet:
					if newTerm in q and 'escapehatch' in q:
						escapeQuestions.append(q)

				newQuestion = randrange(0, len(escapeQuestions))
				chosenQuestion = escapeQuestions[newQuestion]
	elif len(final) > 1:
		rand = randrange(0, len(final))
		print "index chosen: " + str(rand)
		chosenQuestion = final[rand]
		print chosenQuestion
	elif len(final) == 1:
		chosenQuestion = final[0]
		print chosenQuestion

	for q in questionSet:
		if chosenQuestion[1] == q[1]:
			print q[1] + " has been used"
			q.append("used")
			print q
	
	# modify current question variable to eventually see if there's a tied in follow up
	global currentQuestion
	currentQuestion = questionSet.index(chosenQuestion)
	currentTheme = chosenQuestion[5]
	print "Current Question: " + str(currentQuestion)
	print "Current Theme: " + currentTheme

	global questionCount
	questionCount += 1
	print questionCount

	# #ask highest scoring question
	print chosenQuestion[0]

	try:
		speak(currentQuestion)
	except IOError:
		pass


# define a message-handler function for the server to call.
def receive_text(addr, tags, stuff, source):

	global savedFile

	print "---"
	print "received new osc msg from %s" % OSC.getUrlStr(source)
	print "with addr : %s" % addr
	print "typetags %s" % tags
	print "data %s" % stuff
	print "---"

	tags = []
	tags.append(stuff[0:stuff.index('*')])
	tags.append(stuff[stuff.index('*') + 1:])
    # stuff = stuff.split('*')

    # print tags
	if "intro" in tags[1]:
		for q in questionSet:
			if q[len(q)-1] == 'used':
				print q
				q.remove(q[len(q)-1])
		savedFile = tags[1][1]
		returnQuestion([[],["intro"]])
	else:
		checkFollowUp(tags)

s.addMsgHandler("/print", receive_text) # adding our function

# Start OSCServer
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