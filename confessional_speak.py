import OSC
import time, threading, pyaudio, wave, sys

questionSet = []
currentQuestion = 0
questionCount = 0
followup = False
text = ''
savedFile = ''

s = OSC.OSCServer( ("localhost", 9000) )
s.addDefaultHandlers()

#load questions
with open('files/questions.csv', 'rU') as f:
	reader = csv.reader(f, delimiter=";")
	for row in reader:
		toAdd = []
		for i in range(0, len(row)):
			toAdd.append(row[i])
		questionSet.append(toAdd);

print "Questions loaded!"

#checking if there's a follow up question present
def checkFollowUp(tagList):

	#sorts tag list into order based on which tags were used the most
	counter = collections.Counter(tagList)
	if counter:
		ordered = counter.most_common()
		tagList = []

		#rebuild tag list based on sorted version
		for word, count in ordered:
			tagList.append(word)

	global followup

	#checking for follow up questions and follow up types based on database -- need to work out more detailed sorting here
	if questionSet[currentQuestion][2] != '' and followup == False:
		followup = True
		print "there's a follow up here"

		#process for hard follow up questions
		if questionSet[currentQuestion][2] == 'hard':
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			# typeResponse()
			listen()

		#process for yes/no answers; should branch in two directions
		elif questionSet[currentQuestion][2] == 'yesno':
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			# typeResponse()
			listen()

		#process for short answers; follow up only returned if the response has "short" in the tag list
		elif questionSet[currentQuestion][2] == 'short' and 'short' in tagList:
			print questionSet[currentQuestion][3]
			try:
				speak(questionSet[currentQuestion][3])
			except IOError:
				pass
			# typeResponse()
			listen()

		#if there's no follow up, return a question the normal way
		else:
			followup = False
			returnQuestion(tagList)

	#if we are currently on a follow up question:
	elif followup == True:
		#are we currently on an intro question?
		if questionSet[currentQuestion][5] == 'intro':
			followup = False
			returnQuestion(['warmup'])
		elif questionSet[currentQuestion][3] != 'intro':
			followup = False
			returnQuestion(tagList)

	#intro question with no follow up
	elif questionSet[currentQuestion][5] == 'intro':
		returnQuestion(['warmup'])

	#exit automatically after 30 minutes have passed
	elif elapsedTime > 1800:
		goodbye()

	#if no conditions have been met after all of that, return a question the normal way
	else:
		returnQuestion(tagList)

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
		if q[len(q) - 1] != "used":
			# print q

			#only looking for questions that match the most heavily used tag
			for i in range(5, len(q)):
				if q[i] == tagList[0] and len(q) > 6:
					questionScore = 1
					print q[0] + ", score: " + str(questionScore)

					for j in range(1, len(tagList)):
						if q[i] == tagList[j]:
							# add to question score
							questionScore += 1
							print q[0] + ", score: " + str(questionScore)

				elif q[i] == tagList[0] and len(q) <= 6:
					# print "Question that fits: "
					questionScore = 1
					print q[0] + ", score: " + str(questionScore)

				else:
					pass

		#append to list of okay questions
		if questionScore > 0:
			if questionScore > score:
				#clears out list if there's a score higher than the current one
				selection = []
				selection.append(q)
				score = questionScore
			elif questionScore == score:
				selection.append(q)

	# print selection
	if len(selection) > 0:
		rand = randrange(0, len(selection))
		print "index chosen: " + str(rand)
		chosenQuestion = selection[rand]
		# print chosenQuestion

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

	global lastSavedTime
	print "Elapsed time: " + str(time.time() - lastSavedTime)
	lastSavedTime = time.time()

	#ask highest scoring question
	print chosenQuestion[0]

	#write list of tags used & resulting question to transcript
	with open(savedFile, "a") as toSave:
		toSave.write('\n\n')
		toSave.write('Tags found: ' + str(tagList) + '\n')
		toSave.write('Question chosen: ' + chosenQuestion[0] + '\n')

	try:
		speak(chosenQuestion[1])
	except IOError:
		pass

	#clear out question selection list for next response
	selection = []
	global elapsedTime
	elapsedTime = time.time() - startingTime
	print "Time since beginning of program: " + str(elapsedTime) + " seconds"

	#send data out via OSC to let the other program know to start listening

def waitingPeriod():

	#waits for indication to start -- key press for now, will likely be replaced by a sensor
	global startingTime
	global savedFile

	start = int(raw_input('>'))

	if start == 0:
		startingTime = time.time()
		savedFile = "transcript" + str(startingTime) + ".txt"
		print "Program starting"
		returnQuestion(['intro'])
	else:
		print "Sorry, wrong key"
		waitingPeriod()

#if 30 min have passed, go back to waiting period
def goodbye():
	speak("bye")

	for q in questionSet:
		for i in range(0, len(q)):

			#clearing out "used" tags for the next participant
			if q[i] == "used":
				q.remove(q[i])

	waitingPeriod()

# define a message-handler function for the server to call.
def receive_text(addr, tags, stuff, source):
    print "---"
    print "received new osc msg from %s" % OSC.getUrlStr(source)
    print "with addr : %s" % addr
    print "typetags %s" % tags
    print "data %s" % stuff
    print "---"

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