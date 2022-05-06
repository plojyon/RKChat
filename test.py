from subprocess import Popen, PIPE, STDOUT
fake_in = StringIO('')
p = Popen(['echo', '\x1b[6n'], stdout=PIPE, stdin=fake_in, stderr=PIPE)
