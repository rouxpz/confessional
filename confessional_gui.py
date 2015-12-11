from Tkinter import *
import OSC, threading, time
from threading import Thread
from OSC import OSCClient, OSCMessage

minutes = 0
seconds = 0
startTime = 0

calculating = True

s = OSC.OSCServer( ("localhost", 9001) )
s.addDefaultHandlers()

root = Tk()
root.geometry("640x480")

timer = StringVar()
timer.set('')

text = StringVar()
text.set('')

w = Label(root, textvariable = timer, relief=RAISED)
w.grid(row=10)
w.pack()

spoken = Label(root, textvariable = text)
spoken.pack()

terms = ["belief", "childhood", "hurt", "love", "secret", "sex", "worry", "wrong", "start"]

def calculateTime(event=None):
	global minutes, startTime
	seconds = time.time() - startTime
	if seconds > 60:
		minutes += 1
		seconds = 0
		startTime = time.time()
	timer.set(str(int(minutes)).zfill(2) + ":" + str(int(seconds)).zfill(2))
	root.after(1000, calculateTime)

def transcribeSpoken(addr, tags, stuff, source):
	global text
	print "----"
	print "received new osc msg from %s" % OSC.getUrlStr(source)
	print "with addr : %s" % addr
	print "typetags %s" % tags
	print "data %s" % stuff
	print "---"

	if text.get() != stuff[0]:
		text.set(stuff[0])
		root.after(5, transcribeSpoken)

def setTheme(term):
	global startTime
	if term == 'start':
		startTime = time.time()
		root.after(1000, calculateTime)
	print term + " selected as theme!"
	print "Opening OSC"
	client = OSCClient()
	client.connect( ("localhost", 8080) )
	msg = OSCMessage()
	msg.setAddress("/print")
	msg.append(term)
	client.send(msg)
	print "Closing OSC"
	client.close()
	return

s.addMsgHandler("/print", transcribeSpoken) # adding our function
print "\nStarting OSCServer. Use ctrl-C to quit."
st = threading.Thread(target = s.serve_forever)
st.start()


for t in terms:
	b = Button(root, text=t)
	b.configure(command=lambda t=t: setTheme(t))
	b.pack(side=LEFT)

root.mainloop()