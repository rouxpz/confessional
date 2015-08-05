import OSC, csv, time, threading, pyaudio, wave, sys, collections
from random import randrange
from OSC import OSCClient, OSCMessage

questionSet = []
currentQuestion = 0
questionCount = 0
onFollowup = False
text = ''
savedFile = ''

terms = ["belief", "childhood", "crazy", "family", "hurt", "love", "money", "secret", "sex", "trust", "work", "worry", "wrong"]

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

	# for t in tagList:
	# 	#sorts tag list into order based on which tags were used the most
	# 	counter = collections.Counter(t)
	# 	if counter:
	# 		ordered = counter.most_common()
	# 		t = []

	# 		#rebuild tag list based on sorted version
	# 		for word, count in ordered:
	# 			t.append(word)

	# 	orderedTags.append(t)

	global currentQuestion
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
			response = str(raw_input('yes no question >'))
			if response == 'yes':
				if questionSet[currentQuestion][3] != '':
					for j in range(0, len(questionSet)):
						if questionSet[currentQuestion][3] == questionSet[j][1]:
							print "next question: " + questionSet[j][1]
							tempQuestion = j
							speak(j)
					currentQuestion = tempQuestion

				else:
					returnQuestion(tagList)

			elif response == 'no':
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

	#exit automatically after 30 minutes have passed
	# elif elapsedTime > 1800:
	# 	goodbye()

	#if no conditions have been met after all of that, return a question the normal way
	else:
		returnQuestion(tagList)

#computer speaking back to you if exit condition is not met
def speak(number):

	global savedFile

	with open(savedFile, "a") as toSave:
		toSave.write('\n')
		toSave.write('Question: ' + questionSet[number][0])
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
	msg.append("Listen now")
	client.send(msg)
	print "Closing OSC"
	client.close()

def getKey(item):
	return item[1]

#selecting a question to return to participant
def returnQuestion(tagList):

	#integrate "notfirst" and "first" tags in here
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

	if len(narrowed) == 1:
		print narrowed
		final.append(narrowed[0])
	elif len(narrowed) > 1:
		print "Choosing from tags"
		# print narrowed
		# go through tags to find matches
		for t in tagList[1]:
			# print t
			for n in narrowed:
				# print n
				if n[6] != 'followup':
					for i in range(5, 8):
						if n[i] == t:
							print n[0]
							final.append(n)
	elif len(narrowed) == 0:
		print "Choosing from tags"
		# go through tags to find matches
		for t in tagList[1]:
			# print t
			for q in questionSet:
				if q[len(q)-1] != "used" and 'followup' not in q:

					for i in range(5, len(q)):
						if q[i] == t:
							print q[0]
							final.append(q)

	# print final

	if len(final) > 1:
		rand = randrange(0, len(final))
		print "index chosen: " + str(rand)
		chosenQuestion = final[rand]
		print chosenQuestion
	elif len(final) == 1:
		chosenQuestion = final[0]
		print chosenQuestion
	elif len(final) < 1 and len(narrowed) > 1:
		# print "elaboration needed"
		rand = randrange(0, len(narrowed))
		print "index chosen: " + str(rand)
		chosenQuestion = narrowed[rand]
	else:
		if questionSet[currentQuestion][5] == 'intro':
			returnQuestion([[], ['warmup']])
		elif questionSet[currentQuestion][5] == 'warmup':
			returnQuestion([[], ['gettingwarmer']])
		elif questionSet[currentQuestion][5] == 'gettingwarmer':
			returnQuestion([[], ['aboutyou']])
		else:
			newTerm = randrange(0, len(terms))
			returnQuestion([[], [terms[newTerm]]])

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

	# global lastSavedTime
	# print "Elapsed time: " + str(time.time() - lastSavedTime)
	# lastSavedTime = time.time()

	# #ask highest scoring question
	print chosenQuestion[0]

	# #write list of tags used & resulting question to transcript
	# with open(savedFile, "a") as toSave:
	# 	toSave.write('\n\n')
	# 	toSave.write('Tags found: ' + str(tagList) + '\n')
	# 	toSave.write('Question chosen: ' + chosenQuestion[0] + '\n')

	try:
		speak(currentQuestion)
	except IOError:
		pass

	#clear out question selection list for next response
	# selection = []
	# global elapsedTime
	# elapsedTime = time.time() - startingTime
	# print "Time since beginning of program: " + str(elapsedTime) + " seconds"


#if 30 min have passed, go back to waiting period
# def goodbye():
# 	speak("bye")

# 	for q in questionSet:
# 		for i in range(0, len(q)):

# 			#clearing out "used" tags for the next participant
# 			if q[i] == "used":
# 				q.remove(q[i])

	# waitingPeriod()

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